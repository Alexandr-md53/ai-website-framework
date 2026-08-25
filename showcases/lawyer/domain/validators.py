import re
from typing import List, Optional
from showcases.lawyer.domain.models import Attorney, Service, ConsultationRequest


class ConsultationRequestValidator:
    EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    def validate(
        self,
        request: ConsultationRequest,
        attorney: Optional[Attorney],
        service: Optional[Service],
    ) -> List[str]:
        errors: List[str] = []

        if not re.match(self.EMAIL_REGEX, request.client_email or ""):
            errors.append("Invalid client email address")

        if attorney and service:
            provides_service = any(
                service.id in [s.id for s in pa.services]
                for pa in attorney.practice_areas
            )
            if not provides_service:
                errors.append("Attorney does not provide the requested service")

        return errors
