from typing import List, Iterator

from pydantic import BaseModel, Field, AnyHttpUrl, RootModel, ConfigDict


class UserRatingSchema(BaseModel):
    adequacy_score: int = Field(alias="AdequacyScore")
    negative_reviews: int = Field(alias="NegativeReviews")
    politeness_score: int = Field(alias="PolitenessScore")
    positive_reviews: int = Field(alias="PositiveReviews")
    price_score: int = Field(alias="PriceScore")
    punctuality_score: int = Field(alias="PunctualityScore")
    quality_score: int = Field(alias="QualityScore")
    summary_reviews: int = Field(alias="SummaryReviews")
    summary_score: int = Field(alias="SummaryScore")

    model_config = ConfigDict(validate_by_name=True)



class CreatorSchema(BaseModel):
    id: int = Field(alias="Id")
    avatar_url: AnyHttpUrl = Field(alias="Avatar")
    rating: UserRatingSchema = Field(alias="Rating")
    username: str = Field(alias="UserName")

    model_config = ConfigDict(validate_by_name=True)



class TaskSchema(BaseModel):
    id: int = Field(alias="Id")
    name: str = Field(alias="Name")
    is_marker: bool = Field(alias="IsMarker")
    price: float = Field(alias="PriceAmount")
    status: str = Field(alias="StatusText")
    status_flag: str = Field(alias="StatusFlag")
    category: str = Field(alias="CategoryFlag")  # for example "photoshop" ???
    address: str | None = Field(alias="Address")
    url: str = Field(alias="Url")
    datetime: str = Field(alias="DateTimeString")
    is_mine: bool = Field(alias="IsMine") # ???
    is_draft: bool = Field(alias="IsDraft")
    creator: CreatorSchema = Field(alias="CreatorInfo")
    viewed: bool = Field(alias="Viewed")
    is_regular: bool = Field(alias="IsRegular")
    price_range_id: int | None = Field(alias="PriceRangeId")
    budget_description: str | None = Field(alias="BudgetDescription")
    is_sbr: bool = Field(alias="IsSbr")  # ???
    admission: str | None = Field(alias="Admission")  # ???
    is_b2b: bool = Field(alias="IsB2B")
    offers_count: int = Field(alias="OffersCount")
    distance: float| None = Field(alias="Distance")
    is_actual: bool = Field(alias="IsActual")
    is_offered: bool = Field(alias="IsOffered")
    is_offer_rejected: bool = Field(alias="IsOfferRejected")

    model_config = ConfigDict(validate_by_name=True)


class TaskListSchema(RootModel[list[TaskSchema]]):
    def __iter__(self) -> Iterator[TaskSchema]:
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)