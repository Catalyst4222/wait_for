# interactions-wait-for

[![PyPI - Downloads](https://img.shields.io/pypi/dm/interactions-wait-for?color=blue&style=for-the-badge)](https://pypi.org/project/interactions-wait-for/)

Extension for interactions.py which implements `wait_for`

## Installation

```
pip install -U interactions-wait-for
```

--------------------------------------

# `wait_for`

## Benefits

- An actual `wait_for`
- Asynchronous checks
- Timeouts
- Doesn't overwrite any library code

## So what is this so-called `wait_for`?

`wait_for` is an awaitable future that waits for a specific event, and returns the result.

Use cases:

- Waiting for an interaction or message
- Continue commands after response
- Unlike events:
  - You keep data from your slash command
  - You can listen for a response with a timer and a check
  - You can do stuff when timed out

## Okay, but how do I use it?

You import the `wait_for` library like this:

```py
from interactions.ext import wait_for
```

Here is an example code which shows you how to wait for a message, with an asynchronous check and a timeout:

```py
from interactions import Client, Message
from interactions.ext.wait_for import wait_for, setup
import asyncio

bot = Client(token="...")

# apply hooks to the class
setup(bot)


@bot.command(
    name="test", description="this is just a test command."
)
async def test(ctx):
    await ctx.send("grabbing a message...")

    # A simple example check function.
    # Returns True if the original author is the same as the user invoking the wait_for.
    # Returns False if another member is attempting to invoke the wait_for
    async def check(msg):
        if int(msg.author.id) == int(ctx.author.user.id):
            return True
        await ctx.send("I wasn't asking you")
        return False

    try:
        # Define the wait_for.
        # This particular example listens for the raw on_message_create event which then returns a Message object.
        # With this, you have the ability to read the content (if the privileged intent has been
        # approved in the Discord Dev dashboard), any attachments, stickers, etc.
        msg: Message = await wait_for(
            bot, "on_message_create", check=check, timeout=15
        )
        # Afterwards, here you can put your code to execute after the wait_for has been fulfilled,
        # the checks have passed, and the timeout has not been reached.
    except asyncio.TimeoutError:
        # If your specified timeout reaches its end, here you may add your code for that condition.
        return await ctx.send("You said nothing :(")


bot.start()
```

--------------------------------------

# `wait_for_component`

## What's the difference between `wait_for` and `wait_for_component`?

While you could wait for a component click with `wait_for`, `wait_for_component` is designed specifically to get a response from any one of many components that you can pass through as a list. You can also add messages to the `wait_for_component` so that it will check if the component clicked is in any one of the messages specified.

## Okay, but how do I use it?

Here is an example code which shows you how to wait for a message, with an asynchronous check and a timeout:

```py
from interactions import Client, ComponentContext, Button
from interactions.ext.wait_for import setup
import asyncio

bot = Client(token="...")

# apply hooks to the class
setup(bot)


@bot.command(
    name="test", description="this is just a test command."
)
async def test(ctx):
    button = Button(style=1, label="testing", custom_id="testing")
    await ctx.send("grabbing a click...", components=button)

    async def check(button_ctx):
        if int(button_ctx.author.user.id) == int(ctx.author.user.id):
            return True
        await ctx.send("I wasn't asking you!", ephemeral=True)
        return False

    try:
        # Like before, this wait_for listens for a certain event, but is made specifically for components.
        # Although, this returns a new Context, independent of the original context.
        button_ctx: ComponentContext = await bot.wait_for_component(
            components=button, check=check, timeout=15
        )
        # With this new Context, you're able to send a new response.
        await button_ctx.send("You clicked it!")
    except asyncio.TimeoutError:
        # When it times out, edit the original message and remove the button(s)
        return await ctx.edit(components=[])


bot.start()
```

--------------------------------------

## *async* wait_for

Waits for an event once, and returns the result.

Unlike event decorators, this is not persistent, and can be used to only proceed in a command once an event happens.

### Arguments*

- `name: str`: The event to wait for
- `?check: Callable[..., bool]`: A function or coroutine to call, which should return a truthy value if the data should be returned
- `?timeout: float`: How long to wait for the event before raising an error

### Returns

The value of the dispatched event

### Raises

`asyncio.TimeoutError`

--------------------------------------

## *async* wait_for_component

Waits for a component to be interacted with, and returns the resulting context.

### Arguments

- `components: str | Button | SelectMenu | list[str | Button | SelectMenu]`: The component(s) to wait for
- `messages: int | Message | list[int | Message]`: The message(s) to check for
- `?check: Callable[..., bool]`: A function or coroutine to call, which should return a truthy value if the data should be returned
- `?timeout: float`: How long to wait for the event before raising an error

### Returns

The `ComponentContext` of the dispatched event

### Raises

`asyncio.TimeoutError`
