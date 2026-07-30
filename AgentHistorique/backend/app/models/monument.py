from typing import TYPE_CHECKING

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from sqlalchemy import Column
except ImportError:  # pragma: no cover
    Column = None

from app.database import Base

if TYPE_CHECKING:
    from app.models.circuit_monument import CircuitMonument
    from app.models.monument_distance import MonumentDistance


class Monument(Base):
    """Maps to the existing sig_dourbia.monuments table."""

    __tablename__ = "monuments"

    id: Mapped[str] = mapped_column("id_monument", String, primary_key=True)
    name_fr: Mapped[str] = mapped_column("nom_monument_fr", String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column("nom_monument_en", String(255), nullable=True)
    name_ar: Mapped[str | None] = mapped_column("nom_monument_ar", String(255), nullable=True)
    priority: Mapped[float | None] = mapped_column("priorit", Float, nullable=True)
    latitude: Mapped[str | None] = mapped_column("latitude_monument", String(50), nullable=True)
    longitude: Mapped[str | None] = mapped_column("longitude_monument", String(50), nullable=True)
    status: Mapped[str | None] = mapped_column("statut_monument", String(100), nullable=True)
    importance: Mapped[str | None] = mapped_column("importance_monument", String(100), nullable=True)
    accessibility: Mapped[str | None] = mapped_column("accessibilite_monument", String(100), nullable=True)
    relief: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column("adresse_monument", String(500), nullable=True)
    description_fr: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    affectation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    conservation_state: Mapped[float | None] = mapped_column("etat_conservation", Float, nullable=True)
    visit_duration_minutes: Mapped[float | None] = mapped_column("duree_visite_en_min", Float, nullable=True)
    opening_time_summer: Mapped[str | None] = mapped_column("horaire_ouverture_ete", String(50), nullable=True)
    closing_time_summer: Mapped[str | None] = mapped_column("horaire_fermeture_ete", String(50), nullable=True)
    opening_time_winter: Mapped[str | None] = mapped_column("horaire_ouverture_hiver", String(50), nullable=True)
    closing_time_winter: Mapped[str | None] = mapped_column("horaire_fermeture_hiver", String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column("telephone_site", String(50), nullable=True)
    dominant_period: Mapped[str | None] = mapped_column("epoque_dominante", String(100), nullable=True)
    secondary_period: Mapped[str | None] = mapped_column("epoque_secondaire", String(100), nullable=True)
    third_period: Mapped[str | None] = mapped_column(
        "troisieme_epoque", String(100), nullable=True
    )
    function: Mapped[str | None] = mapped_column("fonction_monument", String(100), nullable=True)
    price_resident: Mapped[float | None] = mapped_column("tarif_resident", Float, nullable=True)
    price_student: Mapped[float | None] = mapped_column("tarif_tudiant", Float, nullable=True)
    price_foreign: Mapped[float | None] = mapped_column("tarif_tranger", Float, nullable=True)
    price_teacher: Mapped[str | None] = mapped_column("tarif_enseingant", String(50), nullable=True)
    price_senior: Mapped[str | None] = mapped_column("tarif_retraitee", String(50), nullable=True)
    price_child: Mapped[float | None] = mapped_column("tarif_enfant", Float, nullable=True)
    panoramic_image_url: Mapped[str | None] = mapped_column("image_panoramique", String(500), nullable=True)
    model_object_url: Mapped[str | None] = mapped_column("modele_obj", String(500), nullable=True)
    video_url_fr: Mapped[str | None] = mapped_column("url_video_fr", String(500), nullable=True)
    video_url_en: Mapped[str | None] = mapped_column("uri_video_en", String(500), nullable=True)
    video_url_ar: Mapped[float | None] = mapped_column("uri_video_ar", Float, nullable=True)
    video_360_url: Mapped[str | None] = mapped_column("lien_video_360", String(500), nullable=True)
    video_3d_url: Mapped[str | None] = mapped_column("lien_video_3d", String(500), nullable=True)
    audio_url_fr: Mapped[str | None] = mapped_column("enregistrement_audio_fr", String(500), nullable=True)
    audio_url_en: Mapped[str | None] = mapped_column("enregistrement_audio_en", String(500), nullable=True)
    audio_url_ar: Mapped[float | None] = mapped_column("enregistrement_audio_ar", Float, nullable=True)

    @property
    def latitude_float(self) -> float | None:
        if not self.latitude:
            return None
        try:
            return float(self.latitude.replace(",", "."))
        except ValueError:
            return None

    @property
    def longitude_float(self) -> float | None:
        if not self.longitude:
            return None
        try:
            return float(self.longitude.replace(",", "."))
        except ValueError:
            return None

    circuit_links: Mapped[list["CircuitMonument"]] = relationship(
        back_populates="monument",
    )
    outgoing_distances: Mapped[list["MonumentDistance"]] = relationship(
        foreign_keys="MonumentDistance.from_monument_id",
        back_populates="from_monument",
    )
    incoming_distances: Mapped[list["MonumentDistance"]] = relationship(
        foreign_keys="MonumentDistance.to_monument_id",
        back_populates="to_monument",
    )
