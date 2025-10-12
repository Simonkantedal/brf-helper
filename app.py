import streamlit as st
import logging
from pathlib import Path
from typing import Optional

from brf_helper.etl.document_processor import DocumentProcessor
from brf_helper.etl.vector_store import BRFVectorStore
from brf_helper.etl.text_chunker import TextChunker
from brf_helper.llm.embeddings import GeminiEmbeddings
from brf_helper.llm.rag_interface import BRFQueryInterface

logging.basicConfig(level=logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.ERROR)

st.set_page_config(
    page_title="BRF Helper",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource
def get_query_interface() -> BRFQueryInterface:
    embeddings = GeminiEmbeddings()
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports")
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    processor = DocumentProcessor(embeddings, vector_store, chunker)
    return BRFQueryInterface(processor)


@st.cache_resource
def get_document_processor() -> DocumentProcessor:
    embeddings = GeminiEmbeddings()
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports")
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    return DocumentProcessor(embeddings, vector_store, chunker)


def main():
    st.title("🏢 BRF Helper")
    st.markdown("AI-powered analysis of Swedish BRF annual reports")
    
    with st.sidebar:
        st.header("⚙️ Settings")
        
        brf_filter = st.text_input(
            "Filter by BRF name (optional)",
            placeholder="e.g., brf_fribergsgatan_8_2024",
            help="Leave empty to search all BRFs"
        )
        
        show_sources = st.checkbox("Show source citations", value=True)
        
        st.divider()
        
        vector_store = BRFVectorStore(persist_directory="./chroma_db")
        vector_store.create_collection("brf_reports")
        info = vector_store.get_collection_info()
        
        st.metric("Documents in database", info["count"])
        st.caption(f"Collection: {info['name']}")
    
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "🔍 Query", "📤 Upload"])
    
    with tab1:
        st.header("Chat with your BRF reports")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input("Ask a question about BRF reports..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        query_interface = get_query_interface()
                        response = query_interface.chat(
                            message=prompt,
                            brf_name=brf_filter if brf_filter else None
                        )
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        error_msg = f"Error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        if st.button("Clear chat history", type="secondary"):
            st.session_state.messages = []
            st.rerun()
    
    with tab2:
        st.header("Query BRF reports")
        
        question = st.text_area(
            "Ask a question",
            placeholder="E.g., Vad är årets resultat för BRF Fribergsgatan?",
            height=100
        )
        
        if st.button("Submit Query", type="primary", disabled=not question):
            with st.spinner("Processing query..."):
                try:
                    query_interface = get_query_interface()
                    result = query_interface.query(
                        question=question,
                        brf_name=brf_filter if brf_filter else None,
                        include_sources=show_sources
                    )
                    
                    st.subheader("Answer")
                    st.markdown(result["answer"])
                    
                    if show_sources and result.get("sources"):
                        st.subheader("Sources")
                        
                        for i, source in enumerate(result["sources"], 1):
                            with st.expander(f"Source {i}: {source['brf_name']} (Page {source.get('page_number', 'N/A')})"):
                                st.markdown(f"**Relevance:** {source['relevance_score']:.1%}")
                                st.text(source.get("text", "")[:500] + "...")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with tab3:
        st.header("Upload BRF reports")
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            help="Upload a BRF annual report in PDF format"
        )
        
        brf_name_input = st.text_input(
            "BRF Name (optional)",
            placeholder="E.g., BRF Example 2024",
            help="Leave empty to auto-generate from filename"
        )
        
        reset_db = st.checkbox(
            "Reset database before uploading",
            value=False,
            help="Warning: This will delete all existing documents"
        )
        
        if uploaded_file is not None:
            if st.button("Process PDF", type="primary"):
                with st.spinner("Processing PDF..."):
                    try:
                        temp_path = Path(f"/tmp/{uploaded_file.name}")
                        temp_path.write_bytes(uploaded_file.read())
                        
                        processor = get_document_processor()
                        
                        if reset_db:
                            vector_store = BRFVectorStore(persist_directory="./chroma_db")
                            vector_store.create_collection("brf_reports", reset=True)
                        
                        result = processor.process_pdf(
                            temp_path,
                            brf_name=brf_name_input if brf_name_input else None
                        )
                        
                        temp_path.unlink()
                        
                        st.success("✅ PDF processed successfully!")
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("BRF Name", result["brf_name"])
                        col2.metric("Pages", result["num_pages"])
                        col3.metric("Chunks", result["num_chunks"])
                        
                        st.cache_resource.clear()
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"Error processing PDF: {str(e)}")


if __name__ == "__main__":
    main()
