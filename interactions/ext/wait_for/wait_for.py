import asyncio
import logging
import types
import warnings
from inspect import isawaitable
from typing import Any, Awaitable, Callable, List, Optional, TypeVar, Union, cast

from contextlib import suppress
import interactions
from interactions.api.dispatch import Listener  # just to avoid ide things

Client = TypeVar("Client", bound=interactions.Client)

logger = logging.getLogger("wait_for")


class ExtendedListener(interactions.api.dispatch.Listener):
    def __init__(self):
        super().__init__()
        self.extra_events: dict[str, List[asyncio.Future]] = {}

    def dispatch(self, name: str, *args, **kwargs) -> None:
        super().dispatch(name, *args, **kwargs)

        futs = self.extra_events.get(name, [])
        if not futs:
            return

        logger.debug(f"Resolving {len(futs)} futures")

        for fut in futs:
            if fut.done():
                logger.debug(
                    f"A future for the {name} event was already {'cancelled' if fut.cancelled() else 'resolved'}"
                )
            else:
                fut.set_result(args)

        self.extra_events[name] = []

    def add(self, name: str) -> asyncio.Future:
        """
        Returns a Future that will resolve whenever the supplied event is dispatched

        :param name: The event to listen for
        :type name: str
        :return: A future that will be resolved on the next event dispatch with the data given
        :rtype: asyncio.Future
        """
        fut = asyncio.get_event_loop().create_future()
        futures = self.extra_events.get(name, [])
        futures.append(fut)
        self.extra_events[name] = futures
        return fut


interactions.api.dispatch.Listener = ExtendedListener


class WaitForClient(interactions.Client):
    """A Client subclass that adds the wait-for methods, can be instantiated, subclassed, or typecasted"""

    def wait_for(
        self,
        name: str,
        check: Optional[Callable[..., Union[bool, Awaitable[bool]]]] = None,
        timeout: Optional[float] = None,
    ):
        return wait_for(self, name, check, timeout)

    async def wait_for_component(
        self,
        components: Union[
            Union[interactions.Button, interactions.SelectMenu],
            List[Union[interactions.Button, interactions.SelectMenu]],
        ] = None,
        messages: Union[interactions.Message, int, list] = None,
        check: Optional[Callable[..., Union[bool, Awaitable[bool]]]] = None,
        timeout: Optional[float] = None,
    ):
        return wait_for_component(self, components, messages, check, timeout)


async def wait_for(
    bot: Client,
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
            res: tuple = await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            with suppress(ValueError):
                bot._websocket._dispatch.extra_events[name].remove(fut)
            raise

        if check:
            checked = check(*res)
            if isawaitable(checked):
                checked = await checked
            if checked:
                break
            else:
                # The check failed, so try again next time
                logger.info(f"A check failed waiting for the {name} event")

    # I feel like this needs more?
    # yes it did
    if res:
        return res[0] if len(res) == 1 else res


async def wait_for_component(
    bot: Client,
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
                if isinstance(component, (interactions.Button, interactions.SelectMenu)):
                    custom_ids.append(component.custom_id)
                elif isinstance(component, interactions.ActionRow):
                    custom_ids.extend([c.custom_id for c in component.components])
                elif isinstance(component, list):
                    for c in component:
                        if isinstance(c, (interactions.Button, interactions.SelectMenu)):
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
            messages_ids.append(int(messages.id))
        elif isinstance(messages, list):
            for message in messages:
                if isinstance(message, interactions.Message):
                    messages_ids.append(int(message.id))
                else:
                    messages_ids.append(int(message))
        else:  # account for plain ints, string, or Snowflakes
            messages_ids.append(int(messages))

    def _check(ctx: interactions.ComponentContext) -> bool:
        if custom_ids and ctx.data.custom_id not in custom_ids:
            return False
        if messages_ids and int(ctx.message.id) not in messages_ids:
            return False
        if check:
            return check(ctx)
        return True

    return await wait_for(bot, "on_component", check=_check, timeout=timeout)


def setup(
    bot: Client,
    add_method: bool = None,
) -> Union[Client, "WaitForClient"]:
    """
    Apply hooks to a bot to add additional features

    This function is required, as importing alone won't extend the classes

    :param Client bot: The bot instance or class to apply hooks to
    :param bool add_method: If ``wait_for`` should be attached to the bot
    :return Union[Client, "WaitForClient"]: The typecasted Client
    """

    logger.info("Setting up the client")

    if not isinstance(bot, interactions.Client):
        raise TypeError(f"{bot.__class__.__name__} is not interactions.Client!")

    if add_method is not None:
        warnings.warn("add_method is undergoing depreciation, and will be removed in 2.0")

    if add_method or add_method is None:
        bot.wait_for = types.MethodType(wait_for, bot)
        bot.wait_for_component = types.MethodType(wait_for_component, bot)

    # Overwrite the listener with the new one
    if not isinstance(bot._websocket._dispatch, ExtendedListener):
        new_listener = ExtendedListener()
        old_listener = bot._websocket._dispatch
        new_listener.loop = old_listener.loop
        new_listener.events = old_listener.events
        bot._websocket._dispatch = new_listener

    return cast(WaitForClient, bot)
