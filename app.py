import streamlit as st
import logging
from pathlib import Path
from typing import Optional

from brf_helper.etl.document_processor import DocumentProcessor
from brf_helper.etl.vector_store import BRFVectorStore
from brf_helper.etl.text_chunker import TextChunker
from brf_helper.llm.embeddings import GeminiEmbeddings
from brf_helper.llm.rag_interface import BRFQueryInterface
from brf_helper.database.db import BRFDatabase
from brf_helper.analysis.brf_analyzer import BRFAnalyzer, BRFMetrics
from brf_helper.analysis.red_flag_detector import RedFlagDetector, RedFlagSeverity

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


def get_database() -> BRFDatabase:
    """Get a new database connection (not cached due to SQLite threading)"""
    return BRFDatabase("./data/brf_analysis.db")


def get_available_brfs():
    """Get list of BRFs with metrics from database"""
    db = get_database()
    brfs = db.list_all_brfs(with_metrics_only=True)
    db.close()
    return [(brf.brf_name, brf.id) for brf in brfs]


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
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Analysis", "💬 Chat", "🔍 Query", "📤 Upload"])
    
    with tab1:
        st.header("BRF Financial Analysis Dashboard")
        
        # Get available BRFs
        available_brfs = get_available_brfs()
        
        if not available_brfs:
            st.info("No BRF analysis data available. Upload PDFs and extract metrics first using the Upload tab.")
        else:
            # BRF selector
            brf_names = [name for name, _ in available_brfs]
            selected_brf = st.selectbox(
                "Select BRF to analyze",
                options=brf_names,
                index=0
            )
            
            if selected_brf:
                db = get_database()
                data = db.get_brf_with_metrics(selected_brf)
                db.close()
                
                if data and data.brf.has_metrics:
                    # Convert metrics to BRFMetrics format
                    metrics_dict = {}
                    if data.metrics:
                        for key in ['annual_result', 'operating_result', 'total_debt', 'equity', 'solvency_ratio',
                                    'liquid_assets', 'cash_flow', 'interest_costs', 'annual_fee_per_sqm', 
                                    'maintenance_reserves']:
                            value = getattr(data.metrics, key, None)
                            if value is not None:
                                metrics_dict[key] = value
                    
                    if data.brf.building_year:
                        metrics_dict['building_year'] = data.brf.building_year
                    if data.brf.num_apartments:
                        metrics_dict['num_apartments'] = data.brf.num_apartments
                    if data.brf.total_area:
                        metrics_dict['total_area'] = data.brf.total_area
                    
                    # Compute analysis
                    with st.spinner("Computing analysis..."):
                        brf_metrics = BRFMetrics(brf_name=selected_brf, **metrics_dict)
                        
                        query_interface = get_query_interface()
                        analyzer = BRFAnalyzer(query_interface)
                        health_score = analyzer.calculate_health_score(brf_metrics)
                        
                        detector = RedFlagDetector()
                        red_flag_report = detector.detect_red_flags(brf_metrics)
                    
                    # Display health scores
                    st.subheader("🏥 Financial Health Score")
                    
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    
                    def get_score_color(score):
                        if score >= 80:
                            return "🟢"
                        elif score >= 65:
                            return "🟡"
                        elif score >= 50:
                            return "🟠"
                        else:
                            return "🔴"
                    
                    with col1:
                        st.metric(
                            "Overall",
                            f"{health_score.overall_score}/100",
                            delta=None,
                            help="Overall financial health"
                        )
                        st.markdown(f"{get_score_color(health_score.overall_score)} {health_score.overall_score}/100")
                    
                    with col2:
                        st.metric("Financial Stability", f"{health_score.financial_stability_score}/100")
                        st.markdown(f"{get_score_color(health_score.financial_stability_score)}")
                    
                    with col3:
                        st.metric("Cost Efficiency", f"{health_score.cost_efficiency_score}/100")
                        st.markdown(f"{get_score_color(health_score.cost_efficiency_score)}")
                    
                    with col4:
                        st.metric("Liquidity", f"{health_score.liquidity_score}/100")
                        st.markdown(f"{get_score_color(health_score.liquidity_score)}")
                    
                    with col5:
                        st.metric("Debt Management", f"{health_score.debt_management_score}/100")
                        st.markdown(f"{get_score_color(health_score.debt_management_score)}")
                    
                    with col6:
                        st.metric("Maintenance", f"{health_score.maintenance_readiness_score}/100")
                        st.markdown(f"{get_score_color(health_score.maintenance_readiness_score)}")
                    
                    st.divider()
                    
                    # Display red flags
                    st.subheader("⚠️ Red Flag Analysis")
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("Risk Level", red_flag_report.overall_risk_level)
                    with col2:
                        st.metric("🔴 Critical", red_flag_report.critical_count)
                    with col3:
                        st.metric("🟠 High", red_flag_report.high_count)
                    with col4:
                        st.metric("🟡 Medium", red_flag_report.medium_count)
                    with col5:
                        st.metric("🟢 Low", red_flag_report.low_count)
                    
                    if red_flag_report.red_flags:
                        st.markdown("### Detected Issues")
                        
                        for flag in red_flag_report.red_flags:
                            severity_emoji = {
                                RedFlagSeverity.CRITICAL: "🔴",
                                RedFlagSeverity.HIGH: "🟠",
                                RedFlagSeverity.MEDIUM: "🟡",
                                RedFlagSeverity.LOW: "🟢"
                            }.get(flag.severity, "⚪")
                            
                            with st.expander(f"{severity_emoji} {flag.title} ({flag.severity.value.upper()})"):
                                st.markdown(f"**Category:** {flag.category.value}")
                                st.markdown(f"**Description:** {flag.description}")
                                st.markdown(f"**Impact:** {flag.impact}")
                                st.markdown(f"**Recommendation:** {flag.recommendation}")
                                if flag.evidence:
                                    st.markdown(f"**Evidence:** {flag.evidence}")
                    else:
                        st.success("✅ No red flags detected!")
                    
                    st.divider()
                    
                    # Key metrics table
                    st.subheader("📊 Key Metrics")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if data.metrics.annual_result is not None:
                            st.metric("Årets resultat", f"{data.metrics.annual_result:,.0f} kr")
                        if data.metrics.operating_result is not None:
                            st.metric("Rörelseresultat", f"{data.metrics.operating_result:,.0f} kr")
                        if data.metrics.solvency_ratio is not None:
                            st.metric("Soliditet", f"{data.metrics.solvency_ratio:.1f}%")
                        if data.metrics.liquid_assets is not None:
                            st.metric("Likvida medel", f"{data.metrics.liquid_assets:,.0f} kr")
                    
                    with col2:
                        if data.metrics.cash_flow is not None:
                            st.metric("Kassaflöde", f"{data.metrics.cash_flow:,.0f} kr")
                        if data.metrics.annual_fee_per_sqm is not None:
                            st.metric("Årsavgift/kvm", f"{data.metrics.annual_fee_per_sqm:.0f} kr")
                        if data.metrics.maintenance_reserves is not None:
                            st.metric("Underhållsreserver", f"{data.metrics.maintenance_reserves:,.0f} kr")
                        if data.brf.building_year:
                            age = 2024 - data.brf.building_year
                            st.metric("Byggår", f"{data.brf.building_year} ({age} år)")
                    
                    # Insights
                    st.divider()
                    st.subheader("💡 Analysis Insights")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if health_score.strengths:
                            st.markdown("**✅ Strengths:**")
                            for strength in health_score.strengths:
                                st.markdown(f"- {strength}")
                    
                    with col2:
                        if health_score.concerns:
                            st.markdown("**⚠️ Concerns:**")
                            for concern in health_score.concerns:
                                st.markdown(f"- {concern}")
                    
                    if health_score.recommendations:
                        st.markdown("**🎯 Recommendations:**")
                        for rec in health_score.recommendations:
                            st.markdown(f"- {rec}")
                
                else:
                    st.warning("No metrics found for this BRF. Run ingestion with --extract-metrics first.")
    
    with tab2:
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
