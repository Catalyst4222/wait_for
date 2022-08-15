import interactions
from typing import Awaitable, Callable, List, Optional, Union
import logging
from asyncio import Future, get_event_loop

from .wait_for import wait_for, wait_for_component

logger = logging.getLogger("wait_for")


class ExtendedListener(interactions.api.dispatch.Listener):
    def __init__(self):
        super().__init__()
        self.extra_events: dict[str, List[Future]] = {}

    def dispatch(self, name: str, /, *args, **kwargs) -> None:
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

    def add(self, name: str) -> Future:
        """
        Returns a Future that will resolve whenever the supplied event is dispatched

        :param name: The event to listen for
        :type name: str
        :return: A future that will be resolved on the next event dispatch with the data given
        :rtype: asyncio.Future
        """
        fut = get_event_loop().create_future()
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
