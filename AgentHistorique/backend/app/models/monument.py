from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.circuit_monument import CircuitMonument


class Monument(Base, TimestampMixin):
    """Maps to Monuments.xlsx."""

    __tablename__ = "monuments"

    # ID_monument can be fractional (e.g. 2.1).
    id: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        primary_key=True,
        autoincrement=False,
    )
    name_fr: Mapped[str] = mapped_column(String(255), nullable=False)  # nom_monument_FR
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)  # nom_monument_EN
    name_ar: Mapped[str | None] = mapped_column(String(255), nullable=True)  # nom_monument_AR
    priority: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)  # priorité
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)  # statut_monument
    importance: Mapped[str | None] = mapped_column(String(100), nullable=True)  # importance_monument
    accessibility: Mapped[str | None] = mapped_column(String(100), nullable=True)  # accessibilite_monument
    relief: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)  # adresse_monument
    description_fr: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    affectation: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Affectation
    conservation_state: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)  # etat_conservation
    visit_duration_minutes: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)  # duree_visite(en min)
    opening_time_summer: Mapped[str | None] = mapped_column(String(50), nullable=True)  # horaire_ouverture_ete
    closing_time_summer: Mapped[str | None] = mapped_column(String(50), nullable=True)  # horaire_fermeture_ete
    opening_time_winter: Mapped[str | None] = mapped_column(String(50), nullable=True)  # horaire_ouverture_hiver
    closing_time_winter: Mapped[str | None] = mapped_column(String(50), nullable=True)  # horaire_fermeture_hiver
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)  # telephone_site
    dominant_period: Mapped[str | None] = mapped_column(String(100), nullable=True)  # epoque_dominante
    secondary_period: Mapped[str | None] = mapped_column(String(100), nullable=True)  # epoque_secondaire
    third_period: Mapped[str | None] = mapped_column(String(100), nullable=True)  # troisieme_epoque
    function: Mapped[str | None] = mapped_column(String(100), nullable=True)  # fonction_monument
    price_resident: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)  # Tarif_resident
    price_student: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)  # Tarif_Étudiant
    price_foreign: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)  # Tarif_Étranger
    price_teacher: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)  # Tarif_enseingant
    price_senior: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)  # Tarif_retraitee
    price_child: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)  # Tarif_enfant
    panoramic_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # image_panoramique
    model_object_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # modele_obj
    video_url_fr: Mapped[str | None] = mapped_column(String(500), nullable=True)  # url_video_FR
    video_url_en: Mapped[str | None] = mapped_column(String(500), nullable=True)  # uri_video_EN
    video_url_ar: Mapped[str | None] = mapped_column(String(500), nullable=True)  # uri_video_AR
    video_360_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # lien_video_360
    video_3d_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # lien_video_3D
    audio_url_fr: Mapped[str | None] = mapped_column(String(500), nullable=True)  # enregistrement_audio_FR
    audio_url_en: Mapped[str | None] = mapped_column(String(500), nullable=True)  # enregistrement_audio_EN
    audio_url_ar: Mapped[str | None] = mapped_column(String(500), nullable=True)  # enregistrement_audio_AR

    circuit_links: Mapped[list["CircuitMonument"]] = relationship(
        back_populates="monument",
    )
