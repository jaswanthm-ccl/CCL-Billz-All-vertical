import os
import utils.constants  # Ensures .env is loaded into os.environ

GALAXY_BASE_URL: str = os.getenv("GALAXY_BASE_URL", "https://auto-mobile.devccl-billzweb.crystalbillz.com")
GALAXY_USER_EMAIL: str | None = os.getenv("GALAXY_USER_EMAIL")
GALAXY_USER_PASSWORD: str | None = os.getenv("GALAXY_USER_PASSWORD")

# Unique per-unit identifier that products and purchases track. The seeded "IMEI" attribute is not unique.
GALAXY_TRACKED_ATTRIBUTE: str = os.getenv("GALAXY_TRACKED_ATTRIBUTE", "Serial Number")
