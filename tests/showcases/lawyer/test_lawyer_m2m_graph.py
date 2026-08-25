from decimal import Decimal
import uuid
import pytest

from showcases.lawyer.domain.models import Attorney, PracticeArea, Service


class TestLawyerM2MGraph:
    def test_attorney_practice_area_m2m_relationship(self):
        """Проверка создания графа M2M связей между адвокатом и практиками."""
        corporate_law = PracticeArea(id=uuid.uuid4(), title="Corporate Law")
        tax_law = PracticeArea(id=uuid.uuid4(), title="Taxation")

        attorney = Attorney(
            id=uuid.uuid4(),
            name="Harvey Specter",
            practice_areas=[corporate_law, tax_law],
        )

        assert len(attorney.practice_areas) == 2
        assert corporate_law in attorney.practice_areas
        assert tax_law in attorney.practice_areas

    def test_practice_area_services_relationship(self):
        """Проверка привязки юридических услуг к области практики."""
        m_and_a = Service(
            id=uuid.uuid4(),
            title="Mergers & Acquisitions",
            base_fee=Decimal("5000.00"),
        )
        due_diligence = Service(
            id=uuid.uuid4(),
            title="Due Diligence Review",
            base_fee=Decimal("2500.00"),
        )

        corporate_law = PracticeArea(
            id=uuid.uuid4(),
            title="Corporate Law",
            services=[m_and_a, due_diligence],
        )

        assert len(corporate_law.services) == 2
        assert m_and_a in corporate_law.services

    def test_find_attorneys_providing_service(self):
        """Проверка навигации по M2M графу: поиск адвокатов, оказывающих конкретную услугу."""
        contract_review = Service(
            id=uuid.uuid4(),
            title="Contract Review",
            base_fee=Decimal("800.00"),
        )
        civil_litigation = PracticeArea(
            id=uuid.uuid4(),
            title="Civil Litigation",
            services=[contract_review],
        )

        attorney_1 = Attorney(
            id=uuid.uuid4(),
            name="Mike Ross",
            practice_areas=[civil_litigation],
        )
        attorney_2 = Attorney(
            id=uuid.uuid4(),
            name="Louis Litt",
            practice_areas=[],
        )

        attorneys = [attorney_1, attorney_2]

        eligible_attorneys = [
            a
            for a in attorneys
            if any(contract_review in pa.services for pa in a.practice_areas)
        ]

        assert len(eligible_attorneys) == 1
        assert eligible_attorneys[0].name == "Mike Ross"
