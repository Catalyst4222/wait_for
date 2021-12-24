# interactions-wait-for
[![PyPI - Downloads](https://img.shields.io/pypi/dm/interactions-wait-for?color=blue&style=for-the-badge)](https://pypi.org/project/interactions-wait-for/)

Extension for discord-py-interactions which implements `wait_for`

## Installation:
```
pip install -U interactions-wait-for
```

--------------------------------------

# `wait_for`
## Benefits:
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
from interactions.ext.wait_for import wait_for
import asyncio

bot = Client(token="...")

# apply hooks to the class
wait_for.setup(bot)


@bot.command(
    name="test", description="this is just a test command.", scope=817958268097789972
)
async def test(ctx):
    await ctx.send("grabbing a message...")

    async def check(msg):
        if int(msg.author.id) == int(ctx.author.user.id):
            return True
        await ctx.send("I wasn't asking you")
        return False

    try:
        msg: Message = await wait_for(
            bot, "on_message_create", check=check, timeout=15
        )
    except asyncio.TimeoutError:
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
from interactions.ext import wait_for
import asyncio

bot = Client(token="...")

# apply hooks to the class
# add_method adds the wait_for and wait_for_component methods to your bot
wait_for.setup(bot, add_method=True)


@bot.command(
    name="test", description="this is just a test command.", scope=817958268097789972
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
        button_ctx: ComponentContext = await bot.wait_for_component(
            components=button, check=check, timeout=15
        )
    except asyncio.TimeoutError:
        return await ctx.send("You didn't click :(")


bot.start()
```

--------------------------------------

## *async* wait_for

### Arguments:
- `name` - `str`: The event to wait for
- `check` - `Optional[Callable[..., Union[bool, Awaitable[bool]]]]`: A function or coroutine to call, which should return a truthy value if the data should be returned, default `None`
- `timeout` - `Optional[float]`: How long to wait for the event before raising an error

### Returns:
The value of the dispatched event

### Raises:
`asyncio.TimeoutError`

--------------------------------------

## *async* wait_for_component

### Arguments:
- `components` - `Union[Union[Button, SelectMenu], List[Union[Button, SelectMenu]]]`: The component(s) to wait for, default `None`
- `messages` - `Union[interactions.Message, int, list]`: The message to check for, or a list of messages to check for
- `check` - `Optional[Callable[..., Union[bool, Awaitable[bool]]]]`: A function or coroutine to call, which should return a truthy value if the data should be returned, default `None`
- `timeout` - `Optional[float]`: How long to wait for the event before raising an error

### Returns:
The `ComponentContext` of the dispatched event

### Raises:
`asyncio.TimeoutError`
