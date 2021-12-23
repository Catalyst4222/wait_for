import asyncio
from inspect import isawaitable
from typing import Union, Callable, Optional, Any, Awaitable, Type
import types

import interactions
from interactions.api.dispatch import Listener  # just to avoid ide things


class ExtendedListener(interactions.api.dispatch.Listener):
    def __init__(self):
        super().__init__()
        self.extra_events: dict[str, list[asyncio.Future]] = {}

    def dispatch(self, name: str, *args, **kwargs) -> None:
        super().dispatch(name, *args, **kwargs)

        futs = self.extra_events.get(name, [])

        for fut in futs:
            fut.set_result(args)

            futs.remove(fut)

    def add(self, name: str) -> asyncio.Future:
        """
        Returns a Future that will resolve whenever the supplied event is dispatched

        :param name: The event to listen for
        :type name: str
        :return: A future that will be resolved on the next event dispatch with the data given
        :rtype: asyncio.Future
        """
        fut = asyncio.get_event_loop().create_future()
        try:
            futures = self.extra_events[name]
        except KeyError:
            futures = []
            self.extra_events[name] = futures
        futures.append(fut)
        return fut


interactions.api.dispatch.Listener = ExtendedListener


class ExtendedWebSocket(interactions.api.gateway.WebSocket):
    def handle_dispatch(self, event: str, data: dict) -> None:
        super().handle_dispatch(event, data)

        # print(event)

        if event == "INTERACTION_CREATE":
            # print(data)
            if "type" not in data:
                return

            context = self.contextualize(data)
            self.dispatch.dispatch("on_interaction_create", context)

            name: str = interactions.InteractionType(data["type"]).name
            name = "on_" + name.lower()
            print(name)
            self.dispatch.dispatch(name, context)


interactions.api.gateway.WebSocket = ExtendedWebSocket


async def wait_for(bot: interactions.Client, name: str,
                   check: Optional[Callable[..., Union[bool, Awaitable[bool]]]] = None,
                   timeout: Optional[float] = None) -> Any:
    """
    Wait for an event once, and return the result.

    Unlike event decorators, this is not persistent, and can be used to only proceed in a command once an event happens.

    :param bot: The bot that will receive the event
    :type bot: interactions.Client
    :param name: The event to wait for
    :type name: str
    :param check: A function or coroutine to call, which should return a truthy value if the data should be returned
    :type check: Callable
    :param timeout: How long to wait for the event before raising an error
    :type timeout: float
    :return: The value of the dispatched event
    :rtype: Any
    """
    while True:
        fut = bot.websocket.dispatch.add(name=name)
        try:
            res: list = await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            bot.websocket.dispatch.extra_events[name].remove(fut)
            raise

        if check:
            checked = check(*res)
            if isawaitable(checked):
                checked = await checked
            if not checked:
                # The check failed, so try again next time
                continue

        # I feel like this needs more?
        # yes it did
        if not res:
            return
        elif len(res) == 1:
            return res[0]
        return res


def _replace_values(old, new):
    """Change all values on new to the values on old. Useful if neither object has __dict__"""
    for item in dir(old):  # can't use __dict__, this should take everything
        value = getattr(old, item)

        if hasattr(value, "__call__") or isinstance(value, property):
            # Don't need to get callables or properties, that would un-overwrite things
            continue

        try:
            new.__setattr__(item, value)
        except AttributeError:
            pass


def setup(
        bot: interactions.Client,
        add_method: bool = False,
        add_interaction_events: bool = True
) -> None:
    """
    Apply hooks to a bot to add additional features

    This function required, as importing alone won't extend the classes

    :param Client bot: The bot instance or class to apply hooks to
    :param bool add_method: If ``wait_for`` should be attached to the bot
    :param bool add_interaction_events: Whether to add ``on_message_component``, ``on_application_command``, and other interaction event
    """

    if not isinstance(bot, interactions.Client):
        raise TypeError(f"{bot.__class__.__name__} is not interactions.Client!")

    if add_method:
        bot.wait_for = types.MethodType(wait_for, bot)

    if add_interaction_events:
        old_websocket = bot.websocket
        new_websocket = ExtendedWebSocket(old_websocket.intents, old_websocket.session_id, old_websocket.sequence)

        _replace_values(old_websocket, new_websocket)

        bot.websocket = new_websocket

    # Overwrite the listener with the new one
    new_listener = ExtendedListener()
    old_listener = bot.websocket.dispatch
    new_listener.loop = old_listener.loop
    new_listener.events = old_listener.events
    bot.websocket.dispatch = new_listener


