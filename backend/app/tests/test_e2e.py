"""
End-to-End Full Lifecycle Integration Test.
Validates the complete contract simplification workflow:
Upload → Text Extraction → Clause Extraction → AI Risk Assessment →
Dynamic Summary → Vector Chunking & Embeddings → Grounded Q&A Chat →
Standard Benchmark Clause Comparison → Executive PDF Report Generation.
"""
import io
import uuid
from unittest.mock import patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.services.llm_service import MockLLMProvider
from app.services.embedding_service import MockEmbeddingProvider


@pytest.mark.asyncio
async def test_full_contract_simplifier_lifecycle():
    """
    Executes the entire end-to-end application lifecycle across all 7 core SRS
    requirements and all 4 stretch features.
    """
    with patch("app.services.llm_service.LLMService._resolve_provider", return_value=MockLLMProvider()), \
         patch("app.services.embedding_service.EmbeddingService._resolve_provider", return_value=MockEmbeddingProvider()):
        app = create_app()
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Health Check
            health_res = await client.get("/api/health")
            assert health_res.status_code == 200
            assert health_res.json()["status"] == "ok"

            # 2. Document Upload (PDF / TXT) — [SRS-01 & SRS-S04]
            sample_contract_content = """RESIDENTIAL LEASE AGREEMENT

1. TERM AND DURATION
This Lease shall commence on October 1, 2026 and shall continue for a period of one (1) year.

2. RENT AND PAYMENTS
Tenant agrees to pay monthly rent in the amount of $2,000.00 USD on or before the first day of each calendar month. A grace period of 5 calendar days is permitted.

3. AUTOMATIC RENEWAL
This Agreement shall automatically renew for successive terms of 24 months each, unless Tenant provides written notice of non-renewal at least 3 days prior to expiration.

4. INDEMNIFICATION AND LIABILITY
Tenant agrees to indemnify, defend, and hold harmless Landlord from and against any and all claims, liabilities, damages, and legal costs arising from any occurrence on the premises, without limitation.

5. TERMINATION FOR CAUSE
Landlord may terminate this Lease immediately without prior notice upon any perceived breach of rules by Tenant.
"""
            upload_files = {
                "file": ("sample_residential_lease.txt", io.BytesIO(sample_contract_content.encode("utf-8")), "text/plain")
            }
            upload_data = {
                "document_type": "Rental Agreement"
            }

            upload_res = await client.post("/api/documents/upload", files=upload_files, data=upload_data)
            assert upload_res.status_code == 201
            upload_json = upload_res.json()
            doc_id = upload_json["document_id"]
            assert doc_id is not None
            assert upload_json["document_type"] == "Rental Agreement"

            # 3. Verify Page-Level Text Extraction — [SRS-01]
            text_res = await client.get(f"/api/documents/{doc_id}/text")
            assert text_res.status_code == 200
            text_json = text_res.json()
            assert text_json["total_pages"] == 1
            assert "RESIDENTIAL LEASE AGREEMENT" in text_json["pages"][0]["text"]

            # 4. Run AI Clause Extraction & Risk Assessment — [SRS-02, SRS-03, SRS-04]
            analyze_res = await client.post(f"/api/documents/{doc_id}/analyze")
            assert analyze_res.status_code == 200
            analyze_json = analyze_res.json()
            assert analyze_json["status"] == "ANALYZED"
            assert len(analyze_json["clauses"]) >= 3

            # Confirm risk levels and plain-language explanations
            for clause in analyze_json["clauses"]:
                assert clause["risk_level"] in ("LOW", "MEDIUM", "HIGH")
                assert len(clause["explanation"]) > 5
                assert len(clause["reason"]) > 5
                assert len(clause["clause_text"]) > 10

            # 5. Verify Dynamic Risk Summary Aggregation — [SRS-05]
            summary_res = await client.get(f"/api/documents/{doc_id}/summary")
            assert summary_res.status_code == 200
            summary_json = summary_res.json()
            assert summary_json["total_clauses"] == len(analyze_json["clauses"])
            assert summary_json["high"] + summary_json["medium"] + summary_json["low"] == summary_json["total_clauses"]
            assert len(summary_json["overall_summary"]) > 10

            # 6. Document-Grounded Q&A Chat (RAG) — [SRS-06]
            # Case A: Question with answer inside the document
            chat_q1_res = await client.post(
                f"/api/documents/{doc_id}/chat",
                json={"question": "What is the monthly rent amount?"}
            )
            assert chat_q1_res.status_code == 200
            chat_q1_json = chat_q1_res.json()
            assert chat_q1_json["grounded"] is True
            assert len(chat_q1_json["sources"]) >= 1

            # Case B: Question not answered by document / outside law
            chat_q2_res = await client.post(
                f"/api/documents/{doc_id}/chat",
                json={"question": "What does French employment law say about overtime?"}
            )
            assert chat_q2_res.status_code == 200
            chat_q2_json = chat_q2_res.json()
            assert chat_q2_json["grounded"] is False
            assert "couldn't find" in chat_q2_json["answer"].lower() or "not" in chat_q2_json["answer"].lower()

            # 7. Standard Clause Benchmark Comparison — [SRS-S02]
            comp_res = await client.post(f"/api/documents/{doc_id}/compare")
            assert comp_res.status_code == 200
            comp_json = comp_res.json()
            assert comp_json["document_id"] == doc_id
            assert len(comp_json["comparisons"]) >= 3
            assert comp_json["summary"]["total_comparisons"] >= 3

            # Verify deviation level values
            for comp in comp_json["comparisons"]:
                assert comp["deviation_level"] in ("LOW", "MEDIUM", "HIGH")
                assert 0.0 <= comp["similarity_score"] <= 1.0
                assert len(comp["actual_clause"]) > 5
                assert len(comp["benchmark_clause"]) > 5

            # 8. Executive PDF Report Download — [SRS-S03]
            report_res = await client.get(f"/api/documents/{doc_id}/report")
            assert report_res.status_code == 200
            assert report_res.headers["content-type"] == "application/pdf"
            assert len(report_res.content) > 1000
            assert report_res.content.startswith(b"%PDF")

