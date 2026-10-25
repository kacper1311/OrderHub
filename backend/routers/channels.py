import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from database import get_session
from dependencies import get_current_user, require_admin
from models import Channel, User
from models.enums import UserRole
from schemas.channel import ChannelAdminRead, ChannelCreate, ChannelRead, ChannelUpdate

router = APIRouter(prefix="/api/v1/channels", tags=["channels"])


@router.get("", response_model=list[ChannelAdminRead] | list[ChannelRead])
def list_channels(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    channels = session.exec(select(Channel).order_by(Channel.code)).all()
    schema = ChannelAdminRead if user.role == UserRole.ADMIN else ChannelRead
    return [schema.model_validate(channel) for channel in channels]


@router.post("", response_model=ChannelAdminRead, status_code=201, dependencies=[Depends(require_admin)])
def create_channel(data: ChannelCreate, session: Session = Depends(get_session)):
    if session.exec(select(Channel).where(Channel.code == data.code)).first():
        raise HTTPException(status_code=409, detail="Kanał o tym kodzie już istnieje")

    channel = Channel(code=data.code, name=data.name, webhook_secret=data.webhook_secret)
    session.add(channel)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Kanał o tym kodzie już istnieje")
    session.refresh(channel)
    return channel


@router.patch("/{channel_id}", response_model=ChannelAdminRead, dependencies=[Depends(require_admin)])
def update_channel(channel_id: uuid.UUID, data: ChannelUpdate, session: Session = Depends(get_session)):
    channel = session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Nie znaleziono kanału")

    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(channel, field, value)
    session.add(channel)
    session.commit()
    session.refresh(channel)
    return channel
