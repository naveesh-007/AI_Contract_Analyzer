"""
Comparison Repository — persists benchmark templates, standard clauses,
and clause comparisons for documents (SRS-S02).
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comparison import (
    ClauseComparison,
    StandardClause,
    StandardContractTemplate,
)

logger = logging.getLogger(__name__)

# Standard benchmark templates seed data
BENCHMARK_SEED_DATA = [
    {
        "document_type": "Rental Agreement",
        "name": "Standard Residential Lease Benchmark",
        "description": "Standard balanced benchmark provisions for residential lease and rental agreements.",
        "version": "1.0",
        "clauses": [
            {
                "category": "PAYMENT",
                "title": "Rent Payment and Grace Period",
                "benchmark_text": "Tenant shall pay monthly rent on the first day of each calendar month. A reasonable grace period of 5 calendar days is provided before any customary late charge applies.",
                "description": "Customary monthly rent timing with a standard 5-day grace period.",
            },
            {
                "category": "SECURITY_DEPOSIT",
                "title": "Security Deposit and Return Window",
                "benchmark_text": "Landlord shall hold the security deposit in an escrow account. The deposit shall be returned to Tenant within 30 days after lease termination, less itemized deductions for damages beyond normal wear and tear.",
                "description": "Typical 30-day return period with required itemized deductions.",
            },
            {
                "category": "TERMINATION",
                "title": "Termination Notice and Cause",
                "benchmark_text": "Either party may terminate this agreement at the conclusion of the term by providing at least 30 to 60 days written notice. Early termination for breach requires written notice and a 14-day cure period.",
                "description": "Standard 30-60 day written notice with cure period for alleged breaches.",
            },
            {
                "category": "RENEWAL",
                "title": "Lease Renewal and Extension",
                "benchmark_text": "Upon expiration of the initial term, the agreement shall convert to a month-to-month tenancy or may be renewed upon mutual written agreement of both parties with 30 days prior notice.",
                "description": "Balanced renewal mechanism preventing unexpected multi-year lock-in.",
            },
            {
                "category": "MAINTENANCE",
                "title": "Habitability and Repairs",
                "benchmark_text": "Landlord shall maintain the structural integrity, heating, plumbing, electrical, and sanitary facilities in good working order. Tenant shall maintain ordinary cleanliness and promptly notify Landlord of necessary repairs.",
                "description": "Mutual maintenance responsibilities aligned with implied warranty of habitability.",
            },
            {
                "category": "ENTRY",
                "title": "Landlord Right of Entry",
                "benchmark_text": "Landlord may enter the premises for inspections, repairs, or showings during reasonable business hours, provided that Landlord delivers at least 24 hours prior written notice, except in emergencies.",
                "description": "Standard 24-hour advance notice requirement for non-emergency entry.",
            },
            {
                "category": "LIABILITY",
                "title": "Property Liability and Indemnity",
                "benchmark_text": "Each party is responsible for their own negligent acts or willful misconduct. Tenant is encouraged to obtain renter insurance covering personal property.",
                "description": "Balanced mutual negligence standard without unilateral blanket indemnities.",
            },
        ],
    },
    {
        "document_type": "Freelance Contract",
        "name": "Standard Independent Contractor Benchmark",
        "description": "Standard balanced benchmark provisions for freelance and professional service agreements.",
        "version": "1.0",
        "clauses": [
            {
                "category": "PAYMENT",
                "title": "Invoicing and Payment Terms",
                "benchmark_text": "Client shall pay Contractor within Net 15 to Net 30 days of receiving a valid invoice. Late payments shall accrue interest at no more than 1.5% per month or the legal maximum.",
                "description": "Standard Net 15-30 payment terms with reasonable interest.",
            },
            {
                "category": "INTELLECTUAL_PROPERTY",
                "title": "IP Ownership and Transfer",
                "benchmark_text": "Upon receipt of full payment, Contractor assigns all right, title, and interest in the specific deliverables to Client. Contractor retains ownership of pre-existing tools, libraries, and general methodologies.",
                "description": "Assignment conditioned on receipt of full payment, reserving pre-existing tools.",
            },
            {
                "category": "TERMINATION",
                "title": "Termination for Convenience and Payment for Work Done",
                "benchmark_text": "Either party may terminate this agreement without cause upon 14 to 30 days written notice. In the event of early termination, Client shall pay Contractor for all authorized work performed up to the termination date.",
                "description": "Bilateral termination with guaranteed compensation for completed work.",
            },
            {
                "category": "CONFIDENTIALITY",
                "title": "Mutual Non-Disclosure and Confidentiality",
                "benchmark_text": "Both parties agree to protect confidential information using the same degree of care as their own confidential information. Non-disclosure obligations survive for 2 to 3 years after termination.",
                "description": "Bilateral confidentiality with standard 2-3 year survival duration.",
            },
            {
                "category": "LIABILITY",
                "title": "Limitation of Liability Cap",
                "benchmark_text": "Neither party shall be liable for indirect, incidental, or consequential damages. Total liability of either party under this agreement is capped at the total fees paid or payable in the preceding 12 months.",
                "description": "Mutual liability cap equal to 12 months fees, excluding consequential damages.",
            },
            {
                "category": "SCOPE",
                "title": "Scope of Work and Change Orders",
                "benchmark_text": "Any modifications, expansions, or changes to the project scope, deliverables, or deadlines require a written change order signed by both parties specifying additional fees and timeline adjustments.",
                "description": "Formal written change management for scope modifications.",
            },
        ],
    },
    {
        "document_type": "Terms of Service",
        "name": "Standard Online Terms of Service Benchmark",
        "description": "Standard consumer and SaaS platform terms of service benchmark.",
        "version": "1.0",
        "clauses": [
            {
                "category": "TERMINATION",
                "title": "Account Suspension and Termination",
                "benchmark_text": "Company may suspend or terminate user accounts for material violations of these Terms with reasonable notice where practical. Users may terminate their account at any time via account settings.",
                "description": "Termination for material breach with account self-cancellation rights.",
            },
            {
                "category": "PAYMENT",
                "title": "Subscription Billing and Renewal",
                "benchmark_text": "Subscriptions renew automatically on a recurring monthly or annual basis. Users may cancel renewal at any time prior to the billing cycle end date without incurring penalty fees.",
                "description": "Transparent auto-renewal with seamless cancellation before renewal date.",
            },
            {
                "category": "LIABILITY",
                "title": "Disclaimer of Warranties and Liability Cap",
                "benchmark_text": "Services are provided 'as is' without warranties of any kind. Company aggregate liability to user is limited to the greater of $100 or the total amounts paid by user in the prior 12 months.",
                "description": "Standard SaaS liability limitation with monetary floor.",
            },
            {
                "category": "INTELLECTUAL_PROPERTY",
                "title": "User Content License",
                "benchmark_text": "User retains ownership of all content submitted. User grants Company a non-exclusive, worldwide license solely to host, store, display, and deliver user content as needed to operate the service.",
                "description": "Limited non-exclusive operational license without transfer of underlying ownership.",
            },
            {
                "category": "DISPUTE_RESOLUTION",
                "title": "Governing Law and Dispute Resolution",
                "benchmark_text": "These Terms are governed by applicable local state laws. Disputes shall first be submitted to informal dispute resolution for 30 days prior to initiating formal legal proceedings.",
                "description": "Mandatory 30-day informal negotiation window prior to litigation/arbitration.",
            },
            {
                "category": "MODIFICATION",
                "title": "Changes to Terms with Notice",
                "benchmark_text": "Company reserves the right to modify these Terms and will provide at least 30 days advance notice of material changes via email or prominent site notice before amendments take effect.",
                "description": "30-day advance notice requirement for material policy changes.",
            },
        ],
    },
    {
        "document_type": "Other",
        "name": "General Commercial Contract Benchmark",
        "description": "General standard benchmark for commercial and legal agreements.",
        "version": "1.0",
        "clauses": [
            {
                "category": "PAYMENT",
                "title": "Standard Payment Terms",
                "benchmark_text": "Payments shall be made within 30 days of invoice receipt. Disputed invoice amounts must be notified in writing within 15 days.",
                "description": "Standard 30-day payment cycle with prompt dispute notice.",
            },
            {
                "category": "TERMINATION",
                "title": "Mutual Termination and Cure Period",
                "benchmark_text": "Either party may terminate for material breach if such breach remains uncured for 30 days after receiving written notice.",
                "description": "Standard 30-day written cure period before termination.",
            },
            {
                "category": "CONFIDENTIALITY",
                "title": "Mutual Confidentiality",
                "benchmark_text": "Both parties agree to hold proprietary information in confidence and not disclose it to third parties without prior written consent.",
                "description": "Standard mutual duty of confidence.",
            },
            {
                "category": "LIABILITY",
                "title": "Mutual Limitation of Liability",
                "benchmark_text": "Liability for indirect or punitive damages is excluded, with direct liability capped at the contract value.",
                "description": "Standard commercial liability cap.",
            },
        ],
    },
]


class ComparisonRepository:
    """Handles persistence and retrieval of standard benchmark templates and clause comparisons."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_seed_templates(self) -> None:
        """Seeds benchmark templates and benchmark clauses if they do not exist."""
        result = await self.session.execute(select(func.count(StandardContractTemplate.id)))
        count = result.scalar_one()
        if count > 0:
            return

        logger.info("Seeding standard contract benchmark templates...")
        for tpl_data in BENCHMARK_SEED_DATA:
            tpl = StandardContractTemplate(
                id=uuid.uuid4(),
                document_type=tpl_data["document_type"],
                name=tpl_data["name"],
                description=tpl_data["description"],
                version=tpl_data["version"],
            )
            self.session.add(tpl)
            await self.session.flush()

            for c_data in tpl_data["clauses"]:
                clause = StandardClause(
                    id=uuid.uuid4(),
                    template_id=tpl.id,
                    category=c_data["category"],
                    title=c_data["title"],
                    benchmark_text=c_data["benchmark_text"],
                    description=c_data.get("description", ""),
                )
                self.session.add(clause)

        await self.session.flush()
        logger.info("Successfully seeded %d standard benchmark templates.", len(BENCHMARK_SEED_DATA))

    async def get_template_by_document_type(
        self, document_type: str
    ) -> Optional[StandardContractTemplate]:
        """Retrieves standard benchmark template and clauses matching document_type."""
        await self.ensure_seed_templates()

        query = (
            select(StandardContractTemplate)
            .options(selectinload(StandardContractTemplate.clauses))
            .where(StandardContractTemplate.document_type == document_type)
        )
        result = await self.session.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            # Fallback to "Other" or first available template
            fallback_query = (
                select(StandardContractTemplate)
                .options(selectinload(StandardContractTemplate.clauses))
                .where(StandardContractTemplate.document_type == "Other")
            )
            result = await self.session.execute(fallback_query)
            template = result.scalar_one_or_none()

        return template

    async def get_all_templates(self) -> list[StandardContractTemplate]:
        """Retrieves all standard benchmark templates."""
        await self.ensure_seed_templates()
        query = (
            select(StandardContractTemplate)
            .options(selectinload(StandardContractTemplate.clauses))
            .order_by(StandardContractTemplate.name)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_comparisons_by_document(
        self,
        document_id: uuid.UUID,
        deviation_level: Optional[str] = None,
    ) -> list[ClauseComparison]:
        """
        Retrieves all clause comparisons for a document, strictly scoped by document_id.
        """
        query = (
            select(ClauseComparison)
            .options(
                selectinload(ClauseComparison.clause),
                selectinload(ClauseComparison.standard_clause),
            )
            .where(ClauseComparison.document_id == document_id)
        )

        if deviation_level:
            query = query.where(ClauseComparison.deviation_level == deviation_level.upper())

        query = query.order_by(ClauseComparison.created_at)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_comparisons_by_document(self, document_id: uuid.UUID) -> None:
        """Deletes existing comparisons for a document before re-analyzing."""
        await self.session.execute(
            delete(ClauseComparison).where(ClauseComparison.document_id == document_id)
        )
        await self.session.flush()

    async def bulk_create_comparisons(
        self,
        document_id: uuid.UUID,
        comparison_records: list[dict],
    ) -> list[ClauseComparison]:
        """Persists a batch of evaluated clause comparisons."""
        await self.delete_comparisons_by_document(document_id)

        entities: list[ClauseComparison] = []
        for r in comparison_records:
            item = ClauseComparison(
                id=uuid.uuid4(),
                document_id=document_id,
                clause_id=r["clause_id"],
                standard_clause_id=r.get("standard_clause_id"),
                category=r.get("category", "GENERAL"),
                deviation_level=r.get("deviation_level", "LOW"),
                similarity_score=r.get("similarity_score", 0.8),
                comparison_summary=r.get("comparison_summary", ""),
                differences=r.get("differences", []),
            )
            entities.append(item)
            self.session.add(item)

        await self.session.flush()
        return entities
