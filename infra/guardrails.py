"""Cost guardrails and safety limits."""

from __future__ import annotations

import os
import signal
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CostGuard:
    """Session cost guardrails."""
    
    max_droplets: int = 6
    max_session_minutes: int = 60
    droplet_cost_per_hour: float = 0.00893  # s-1vcpu-1gb
    
    _start_time: float = field(default_factory=time.time)
    _droplets_created: int = 0
    
    def __post_init__(self) -> None:
        """Load from environment."""
        self.max_droplets = int(os.getenv("MAX_TEST_DROPLETS", self.max_droplets))
        self.max_session_minutes = int(os.getenv("MAX_SESSION_MINUTES", self.max_session_minutes))
    
    def check_droplet_limit(self) -> bool:
        """Check if we can create another droplet."""
        return self._droplets_created < self.max_droplets
    
    def record_droplet(self) -> None:
        """Record a droplet creation."""
        self._droplets_created += 1
    
    def check_timeout(self) -> bool:
        """Check if session has timed out."""
        elapsed = (time.time() - self._start_time) / 60
        return elapsed < self.max_session_minutes
    
    def estimate_cost(self) -> float:
        """Estimate current session cost."""
        hours = (time.time() - self._start_time) / 3600
        return self._droplets_created * self.droplet_cost_per_hour * hours
    
    def get_summary(self) -> dict[str, Any]:
        """Get session summary."""
        elapsed_minutes = (time.time() - self._start_time) / 60
        return {
            "droplets_created": self._droplets_created,
            "max_droplets": self.max_droplets,
            "elapsed_minutes": round(elapsed_minutes, 2),
            "max_minutes": self.max_session_minutes,
            "estimated_cost_usd": round(self.estimate_cost(), 4),
        }


class SessionGuard:
    """Session-wide safety guard."""
    
    def __init__(self, controller: Any) -> None:
        """Initialize with droplet controller."""
        self.controller = controller
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Setup cleanup on signals."""
        def handler(signum: int, frame: Any) -> None:
            print("\nReceived signal, cleaning up...")
            self.cleanup()
            exit(1)
        
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
    
    def cleanup(self) -> None:
        """Emergency cleanup of all resources."""
        try:
            self.controller.destroy_all()
        except Exception as e:
            print(f"Cleanup error: {e}")
