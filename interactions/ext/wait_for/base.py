from hashlib import md5

from interactions.ext import Base, Version, VersionAuthor


class VersionAuthor(VersionAuthor):
    def __init__(
        self,
        name,
        *,
        shared=False,
        active=True,
        email=None,
    ) -> None:
        """
        :param name: The name of the author.
        :type name: str
        :param shared?: The author's relationship as the main or co-author. Defaults to ``False``.
        :type shared: Optional[bool]
        :param active?: The author's state of activity. Defaults to ``True``.
        :type active: Optional[bool]
        :param email?: The author's email address or point of contact. Defaults to ``None``.
        :type email: Optional[str]
        """
        self.name = name
        self._co_author = shared
        self.active = active
        self.email = email
        self._hash = md5(self.__str__().encode())


class Version(Version):
    __slots__ = ("_authors",)


class Base(Base):
    __slots__ = ("long_description",)


__version__ = "1.0.2"

version = Version(
    version=__version__,
    authors=[VersionAuthor("Catalyst4")],
)

base = Base(
    name="interactions-wait-for",
    version=version,
    link="https://github.com/Catalyst4222/interactions-wait-for",
    description="A wait_for implementation for discord-py-interactions",
    packages=["interactions.ext.wait_for"],
    requirements=["discord-py-interactions>=4.1.0"],
)
