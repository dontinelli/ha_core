"""Entity for Fyta plant image."""

from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.image import (
    Image,
    ImageEntity,
    ImageEntityDescription,
    valid_image_content_type,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FytaConfigEntry, FytaCoordinator
from .entity import FytaPlantEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FytaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the FYTA plant images."""
    coordinator = entry.runtime_data

    description_default = ImageEntityDescription(key="plant_image")
    description_user = ImageEntityDescription(key="plant_image_user")

    entities = []
    for plant_id in coordinator.fyta.plant_list:
        if plant_id in coordinator.data:
            entities.append(
                FytaPlantImageEntity(
                    coordinator,
                    entry,
                    description_default,
                    plant_id,
                    image_type="default",
                )
            )
            entities.append(
                FytaPlantImageEntity(
                    coordinator, entry, description_user, plant_id, image_type="user"
                )
            )

    async_add_entities(entities)

    def _async_add_new_device(plant_id: int) -> None:
        async_add_entities(
            [
                FytaPlantImageEntity(
                    coordinator,
                    entry,
                    description_default,
                    plant_id,
                    image_type="default",
                ),
                FytaPlantImageEntity(
                    coordinator, entry, description_user, plant_id, image_type="user"
                ),
            ]
        )

    coordinator.new_device_callbacks.append(_async_add_new_device)


class FytaPlantImageEntity(FytaPlantEntity, ImageEntity):
    """Represents a Fyta image."""

    entity_description: ImageEntityDescription

    def __init__(
        self,
        coordinator: FytaCoordinator,
        entry: ConfigEntry,
        description: ImageEntityDescription,
        plant_id: int,
        image_type: str = "default",  # "default" or "user"
    ) -> None:
        """Initiatlize Fyta Image entity."""
        super().__init__(coordinator, entry, description, plant_id)
        ImageEntity.__init__(self, coordinator.hass)

        self._image_type = image_type
        # For backward compatibility, keep unique_id and entity_id for default image
        if image_type == "user":
            self._attr_unique_id = f"{entry.entry_id}-{plant_id}-{description.key}"
            self._attr_entity_id = (
                f"image.{self.plant.name.lower().replace(' ', '_')}_user"
            )
            self._attr_name = "User Image"
        else:
            self._attr_unique_id = f"{entry.entry_id}-{plant_id}-plant_image"
            # entity_id is auto-generated, but we keep the key as before
            self._attr_name = "Plant Image"

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        if self._image_type == "user":
            if self._cached_image is None:
                response = await self.coordinator.fyta.get_plant_image(
                    self.plant.user_picture_path
                )
                _LOGGER.debug("Response of downloading user image: %s", response)
                if response is None:
                    _LOGGER.debug(
                        "%s: Error getting new image from %s",
                        self.entity_id,
                        self.plant.user_picture_path,
                    )
                    return None

                content_type, raw_image = response
                self._cached_image = Image(
                    valid_image_content_type(content_type), raw_image
                )

            return self._cached_image.content
        return await ImageEntity.async_image(self)

    @property
    def image_url(self) -> str:
        """Return the image_url for this plant."""
        url = (
            self.plant.user_picture_path
            if self._image_type == "user"
            else self.plant.plant_origin_path
        )

        if url != self._attr_image_url:
            self._cached_image = None
            self._attr_image_last_updated = datetime.now()
        return url
