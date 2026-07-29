from dataclasses import dataclass


@dataclass
class RealCheckConfig:
    """Configuration for a RealCheckEnvironment.

    Unlike TaskGraphConfig, there's no seed - nothing here is stochastic,
    so there's nothing to seed. The one environment-wide setting a real
    subprocess call needs that a simulated one didn't: a timeout, so a
    hung check (a bug in the fixture, an infinite loop) can't stall a run
    forever.

    Attributes:
        timeout: Seconds to wait for a single check's subprocess before
            raising, per node.
    """

    timeout: float = 30.0
