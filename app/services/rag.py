import os
import re
import numpy as np
from pypdf import PdfReader
from openai import OpenAI
from app import db
from app.models import Document, DocumentChunk

class RAGService:
    def __init__(self):
        # We fetch the API key inside init to ensure we read the latest config/env
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
    def _get_client(self):
        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Please set the OPENAI_API_KEY environment variable.")
        return OpenAI(api_key=self.api_key)

    def extract_text_from_pdf(self, file_path):
        """Extract text content page by page from a PDF file."""
        text_pages = []
        try:
            reader = PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_pages.append((i + 1, page_text))
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
        return text_pages

    def chunk_text(self, text_pages, chunk_size=800, chunk_overlap=150):
        """Split text pages into overlapping chunks of defined character size."""
        chunks = []
        
        for page_num, page_text in text_pages:
            # Clean up white spaces
            cleaned_text = re.sub(r'\s+', ' ', page_text).strip()
            
            # Simple window-based text chunking
            start = 0
            while start < len(cleaned_text):
                end = start + chunk_size
                chunk = cleaned_text[start:end]
                
                # Metadata contains the source reference
                chunks.append({
                    'text': chunk,
                    'page_num': page_num
                })
                
                start += (chunk_size - chunk_overlap)
                
        return chunks

    def generate_embeddings(self, texts):
        """Generate vector embeddings for a list of texts using OpenAI API."""
        client = self._get_client()
        try:
            response = client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            raise e

    def process_and_index_document(self, doc_id):
        """Extract text, chunk it, generate embeddings, and store in database."""
        document = Document.query.get(doc_id)
        if not document:
            return False, "Document not found"

        try:
            # 1. Extract text
            if document.file_path.endswith('.pdf'):
                text_pages = self.extract_text_from_pdf(document.file_path)
            elif document.file_path.endswith('.txt'):
                with open(document.file_path, 'r', encoding='utf-8') as f:
                    text_pages = [(1, f.read())]
            else:
                return False, "Unsupported file format"

            if not text_pages:
                return False, "No text could be extracted from the document"

            # 2. Chunk text
            chunks = self.chunk_text(text_pages)
            
            if not chunks:
                return False, "No text chunks generated"

            # 3. Generate embeddings batch-wise to prevent API rate limit issues
            texts_to_embed = [c['text'] for c in chunks]
            
            # Batch size of 100 is safe and fast
            batch_size = 100
            all_embeddings = []
            for i in range(0, len(texts_to_embed), batch_size):
                batch = texts_to_embed[i:i+batch_size]
                embeddings_batch = self.generate_embeddings(batch)
                all_embeddings.extend(embeddings_batch)

            # 4. Save to DB
            for idx, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
                doc_chunk = DocumentChunk(
                    document_id=document.id,
                    text=chunk['text'],
                    chunk_index=idx,
                )
                # Save embedding (using models.py setter which JSON encodes it)
                doc_chunk.embedding = embedding
                db.session.add(doc_chunk)

            # Mark document as processed
            document.processed = True
            db.session.commit()
            return True, f"Indexed {len(chunks)} chunks successfully."

        except Exception as e:
            db.session.rollback()
            print(f"Failed to process document {document.filename}: {e}")
            return False, str(e)

    def retrieve_similar_chunks(self, query, top_k=5):
        """Retrieve the top K most similar text chunks for a query using cosine similarity."""
        # Check if we have chunks in DB
        chunks = DocumentChunk.query.all()
        if not chunks:
            return []

        # 1. Get query embedding
        query_embedding = self.generate_embeddings([query])[0]

        # 2. Load all chunk embeddings and run cosine similarity
        chunk_embeddings = np.array([c.embedding for c in chunks])
        query_emb_arr = np.array(query_embedding)

        # Dot product of embeddings
        dot_products = np.dot(chunk_embeddings, query_emb_arr)
        
        # Norms
        chunk_norms = np.linalg.norm(chunk_embeddings, axis=1)
        query_norm = np.linalg.norm(query_emb_arr)
        
        # Calculate Cosine Similarities (preventing division by zero)
        similarities = dot_products / (chunk_norms * query_norm + 1e-10)

        # 3. Sort by similarity descending and filter out extremely low matches (e.g. < 0.1)
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            # Only return chunks with positive relevance
            if score > 0.15:
                chunk = chunks[idx]
                results.append({
                    'chunk_id': chunk.id,
                    'document_name': chunk.document.filename,
                    'text': chunk.text,
                    'similarity': score
                })
        
        return results

    def query_rag(self, user_query, top_k=5):
        """Execute semantic search, build a context prompt, and query the LLM."""
        # 1. Retrieve matching chunks
        try:
            matched_chunks = self.retrieve_similar_chunks(user_query, top_k=top_k)
        except Exception as e:
            print(f"RAG retrieval error: {e}")
            matched_chunks = []

        # 2. Construct context
        context = ""
        sources = []
        
        if matched_chunks:
            context_blocks = []
            for i, chunk in enumerate(matched_chunks):
                context_blocks.append(f"Source [{i+1}] ({chunk['document_name']}):\n{chunk['text']}")
                sources.append(chunk['document_name'])
            context = "\n\n".join(context_blocks)
            # Deduplicate sources
            sources = list(set(sources))
        else:
            context = "No relevant context found in the database. Rely on general university advice but warn the user that no specific documents were found."

        # 3. Generate response using OpenAI Chat Completions
        system_prompt = (
            "You are UniAssist, a friendly and professional chatbot for university students.\n"
            "Your goal is to answer student questions accurately based ONLY on the provided context blocks.\n"
            "Strict rules:\n"
            "1. Rely on the provided context to answer. If the context does not contain the answer, say that you don't know or that you couldn't find it in the university documents, and offer general advice if helpful.\n"
            "2. Keep your answers concise, structured, and easy to read. Use bullet points where appropriate.\n"
            "3. If you use information from a source block, cite the source name in your response (e.g., [Source Name] or (Source Name)).\n"
            "4. Do not make up facts or university regulations. If rules are ambiguous, advise the user to contact the student affairs office."
        )
        
        user_prompt = f"Context:\n{context}\n\nQuestion: {user_query}\n\nAnswer:"
        
        client = self._get_client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # Try with standard model parameters (gpt-4o-mini, gpt-4o, etc.)
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=800
            )
            answer = response.choices[0].message.content.strip()
            return answer, sources
        except Exception as e:
            error_str = str(e)
            # If it is a reasoning model (like o1 or o3-mini) that does not support temperature or max_tokens
            if "max_tokens" in error_str or "unsupported_parameter" in error_str or "temperature" in error_str:
                try:
                    # Retry with parameters supported by reasoning models
                    response = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_completion_tokens=800
                    )
                    answer = response.choices[0].message.content.strip()
                    return answer, sources
                except Exception as retry_e:
                    print(f"Retry completion failed: {retry_e}")
                    return f"An error occurred while generating the chatbot response: {str(retry_e)}", []
            else:
                print(f"Error generating answer: {e}")
                return f"An error occurred while generating the chatbot response: {str(e)}", []
