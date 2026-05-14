from typing import Tuple


class RateLimiter:
    def check_rate_limit(self, user_id: str, endpoint: str, ip_address: str = None) -> Tuple[bool, int]:
        return True, 0
