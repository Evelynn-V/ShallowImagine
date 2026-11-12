"""ShallowImagine: a deliberately wrong little agent.

The package is intentionally dependency-free. The optional language-model
backends live in ``harness.backends`` and import their heavy dependencies
lazily, so the deterministic harness can run on a bare Python install.
"""

from .pipeline import ShallowImagion, Result

__all__ = ["ShallowImagion", "Result"]
__version__ = "0.1.0"
