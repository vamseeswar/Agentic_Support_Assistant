from app.models import PolicySearchResult
from app.repositories.policy_repository import policy_repository


class PolicyService:
    """Retrieves and grounds answers in the Trendly policy document."""

    def search(self, query: str, top_k: int = 3) -> PolicySearchResult:
        """
        Query the policy document. Returns grounded results with citations.
        If no relevant sections found, returns found=False — the agent must
        say it does not know and offer a human agent.
        """
        return policy_repository.search(query, top_k=top_k)

    def get_full_text(self) -> str:
        return policy_repository.get_full_text()


policy_service = PolicyService()
