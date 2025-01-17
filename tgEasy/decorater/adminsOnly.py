# tgEasy - Easy for a brighter Shine. A monkey pather add-on for Pyrogram
# Copyright (C) 2021 - 2022 Jayant Hegde Kageri <https://github.com/jayantkageri>

# This file is part of tgEasy.

# tgEasy is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# tgEasy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with tgEasy.  If not, see <http://www.gnu.org/licenses/>.

import typing

import pyrogram
from cachetools import TTLCache

from tgEasy.scaffold import Scaffold

from ..helpers import check_rights, handle_error, is_admin

ANON = TTLCache(maxsize=250, ttl=30)


async def anonymous_admin(m: pyrogram.types.Message):
    """
    Helper function for Anonymous Admin Verification
    """
    keyboard = pyrogram.types.InlineKeyboardMarkup(
        [
            [
                pyrogram.types.InlineKeyboardButton(
                    text="Verify!",
                    callback_data=f"anon.{m.message_id}",
                ),
            ]
        ]
    )
    return await m.reply_text(
        "Click here to prove you are admin with the required rights to perform this action!",
        reply_markup=keyboard,
    )


class AdminsOnly(Scaffold):
    async def anonymous_admin_verification(
        client, CallbackQuery: pyrogram.types.CallbackQuery
    ):
        if int(
            f"{CallbackQuery.message.chat.id}{CallbackQuery.data.split('.')[1]}"
        ) not in set(ANON.keys()):
            try:
                await CallbackQuery.message.edit_text("Button has been Expired.")
            except pyrogram.types.RPCError:
                try:
                    await CallbackQuery.message.delete()
                except pyrogram.types.RPCError:
                    pass
            return
        cb = ANON.pop(
            int(f"{CallbackQuery.message.chat.id}{CallbackQuery.data.split('.')[1]}")
        )
        member = await CallbackQuery.message.chat.get_member(CallbackQuery.from_user.id)
        if bool(member.status not in ("creator", "administrator")):
            return await CallbackQuery.answer("You need to be an admin to do this.")
        permission = cb[2]

        if isinstance(permission, str):
            if not await check_rights(
                CallbackQuery.message.chat.id,
                CallbackQuery.from_user.id,
                permission,
                client=client,
            ):
                return await CallbackQuery.message.edit_text(
                    f"You are Missing the following Rights to use this Command:\n{permission}",
                )
        if isinstance(permission, list):
            permissions = ""
            for perm in permission:
                if not await check_rights(
                    CallbackQuery.message.chat.id,
                    CallbackQuery.from_user.id,
                    perm,
                    client=client,
                ):
                    permissions += f"\n{perm}"
                    if not permissions == "":
                        return await CallbackQuery.message.edit_text(
                            f"You are Missing the following Rights to use this Command:{permissions}",
                        )
        try:
            await CallbackQuery.message.delete()
            await cb[1](client, cb[0])
        except pyrogram.errors.exceptions.forbidden_403.ChatAdminRequired:
            return await CallbackQuery.message.edit_text(
                "I must be admin to execute this Command",
            )
        except BaseException as e:
            return await handle_error(e, CallbackQuery)

    def adminsOnly(
        self,
        permission: typing.Union[str, list],
        TRUST_ANON_ADMINS: typing.Union[bool, bool] = False,
    ):
        """
        # `tgEasy.tgClient.adminsOnly`
        - A decorater for running the function only if the admin have the specified Rights.
        - If the admin is Anonymous Admin, it also checks his rights by making a Callback.
        - Parameters:
        - permission (str):
            - Permission which the User must have to use the Functions

        - TRUST_ANON_ADMIN (bool) **optional**:
            - If the user is an Anonymous Admin, then it bypasses his right check.

        # Example
        .. code-block:: python
            from tgEasy import tgClient
            import pyrogram

            app = tgClient(pyrogram.Client())

            @app.command("start")
            @app.adminsOnly("can_change_info")
            async def start(client, message):
                await message.reply_text(f"Hello Admin {message.from_user.mention}")
        """

        def wrapper(func):
            async def decorator(client, message):
                permissions = ""
                if not message.chat.type == "supergroup":
                    return await message.reply_text(
                        "This command can be used in supergroups only.",
                    )
                if message.sender_chat and not TRUST_ANON_ADMINS:
                    ANON[int(f"{message.chat.id}{message.message_id}")] = (
                        message,
                        func,
                        permission,
                    )
                    return await anonymous_admin(message)
                if not await is_admin(
                    message.chat.id,
                    message.from_user.id,
                    client=client,
                ):
                    return await message.reply_text(
                        "Only admins can execute this Command!",
                    )
                if isinstance(permission, str):
                    if not await check_rights(
                        message.chat.id,
                        message.from_user.id,
                        permission,
                        client=client,
                    ):
                        return await message.reply_text(
                            f"You are Missing the following Rights to use this Command:\n{permission}",
                        )
                if isinstance(permission, list):
                    for perm in permission:
                        if not await check_rights(
                            message.chat.id,
                            message.from_user.id,
                            perm,
                            client=client,
                        ):
                            permissions += f"\n{perm}"
                    if not permissions == "":
                        return await message.reply_text(
                            f"You are Missing the following Rights to use this Command:{permissions}",
                        )
                try:
                    await func(client, message)
                except pyrogram.errors.exceptions.forbidden_403.ChatWriteForbidden:
                    await client.leave_chat(message.chat.id)
                except BaseException as exception:
                    await handle_error(exception, message)

            self.__client__.add_handler(
                pyrogram.handlers.CallbackQueryHandler(
                    AdminsOnly.anonymous_admin_verification,
                    pyrogram.filters.regex("^anon."),
                ),
            )
            return decorator

        return wrapper
