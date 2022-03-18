import asyncio
import types
from inspect import isawaitable
from typing import Any, Awaitable, Callable, List, Optional, Union

from interactions.api.dispatch import Listener  # just to avoid ide things

import interactions


class ExtendedListener(interactions.api.dispatch.Listener):
    def __init__(self):
        super().__init__()
        self.extra_events: dict[str, list[asyncio.Future]] = {}

    def dispatch(self, name: str, *args, **kwargs) -> None:
        super().dispatch(name, *args, **kwargs)

        futs = self.extra_events.get(name, [])

        for fut in futs:
            if not fut.done():
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


async def wait_for(
    bot: interactions.Client,
    name: str,
    check: Optional[Callable[..., Union[bool, Awaitable[bool]]]] = None,
    timeout: Optional[float] = None,
) -> Any:
    """
    Waits for an event once, and returns the result.

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
        fut = bot._websocket._dispatch.add(name=name)
        try:
            res: list = await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            bot._websocket._dispatch.extra_events[name].remove(fut)
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


async def wait_for_component(
    bot: interactions.Client,
    components: Union[
        Union[interactions.Button, interactions.SelectMenu],
        List[Union[interactions.Button, interactions.SelectMenu]],
    ] = None,
    messages: Union[interactions.Message, int, list] = None,
    check: Optional[Callable[..., Union[bool, Awaitable[bool]]]] = None,
    timeout: Optional[float] = None,
):
    """
    Waits for a component to be interacted with, and returns the resulting context.

    :param bot: The bot to listen with
    :type bot: interactions.Client
    :param components: The component to wait for
    :type components: Union[interactions.Button, interactions.SelectMenu]
    :param check: A function or coroutine to call, which should return a truthy value if the data should be returned
    :type check: Callable
    :param timeout: How long to wait for the event before raising an error
    :type timeout: float
    :param messages: The message to wait for, or a list of messages to wait for
    :type messages: Union[interactions.Message, int, list]
    :return: The ComponentContext of the dispatched event
    :rtype: interactions.ComponentContext
    """
    custom_ids: List[str] = []
    messages_ids: List[int] = []

    if components:
        if isinstance(components, list):
            for component in components:
                if isinstance(
                    component, (interactions.Button, interactions.SelectMenu)
                ):
                    custom_ids.append(component.custom_id)
                elif isinstance(component, interactions.ActionRow):
                    custom_ids.extend([c.custom_id for c in component.components])
                elif isinstance(component, list):
                    for c in component:
                        if isinstance(
                            c, (interactions.Button, interactions.SelectMenu)
                        ):
                            custom_ids.append(c.custom_id)
                        elif isinstance(c, interactions.ActionRow):
                            custom_ids.extend([b.custom_id for b in c.components])
                        elif isinstance(c, str):
                            custom_ids.append(c)
                elif isinstance(component, str):
                    custom_ids.append(component)
        elif isinstance(components, (interactions.Button, interactions.SelectMenu)):
            custom_ids.append(components.custom_id)
        elif isinstance(components, interactions.ActionRow):
            custom_ids.extend([c.custom_id for c in components.components])
        elif isinstance(components, str):
            custom_ids.append(components)

    if messages:
        if isinstance(messages, interactions.Message):
            messages_ids.append(messages.id)
        elif isinstance(messages, int):
            messages_ids.append(messages)
        elif isinstance(messages, list):
            for message in messages:
                if isinstance(message, interactions.Message):
                    messages_ids.append(message.id)
                elif isinstance(message, int):
                    messages_ids.append(message)

    def _check(ctx: interactions.ComponentContext) -> bool:
        if custom_ids and ctx.data.custom_id not in custom_ids:
            return False
        if messages_ids and ctx.message.id not in messages_ids:
            return False
        if check:
            return check(ctx)
        return True

    return await wait_for(bot, "on_component", check=_check, timeout=timeout)


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
) -> None:
    """
    Apply hooks to a bot to add additional features

    This function is required, as importing alone won't extend the classes

    :param Client bot: The bot instance or class to apply hooks to
    :param bool add_method: If ``wait_for`` should be attached to the bot
    :param bool add_interaction_events: Whether to add ``on_message_component``, ``on_application_command``, and other interaction event
    """

    if not isinstance(bot, interactions.Client):
        raise TypeError(f"{bot.__class__.__name__} is not interactions.Client!")

    if add_method:
        bot.wait_for = types.MethodType(wait_for, bot)
        bot.wait_for_component = types.MethodType(wait_for_component, bot)

    # Overwrite the listener with the new one
    if not isinstance(bot._websocket._dispatch, ExtendedListener):
        new_listener = ExtendedListener()
        old_listener = bot._websocket._dispatch
        new_listener.loop = old_listener.loop
        new_listener.events = old_listener.events
        bot._websocket._dispatch = new_listener
