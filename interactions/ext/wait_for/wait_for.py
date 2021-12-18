from typing import Union
import types

import interactions
from interactions.api.dispatch import Listener  # just to avoid ide things


class ExtendedListener(interactions.api.dispatch.Listener):
    extra_events: dict[str, list]

    def dispatch(self, name: str, *args, **kwargs) -> None:
        super().dispatch(name, *args, **kwargs)

        for task in self.extra_events.get(name, []):



interactions.api.dispatch.Listener = ExtendedListener

def wait_for(self: interactions.Client, event: str):
    ...

# noinspection PyTypeHints
def setup(bot: Union[
    interactions.Client,
    # type(interactions.Client)
]):
    if isinstance(bot, type(interactions.Client)):  # class object
        bot.wait_for = wait_for

    elif isinstance(bot, interactions.Client):  # instance
        bot.wait_for = types.MethodType(wait_for, bot)

    else:
        raise TypeError(f"{bot.__class__.__name__} is not interactions.Client!")

    bot.websocket.dispatch = ExtendedListener()
