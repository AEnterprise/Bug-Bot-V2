import aiohttp
import backoff

from Utils import Configuration

API_BASE = 'https://api.trello.com/1'


class TrelloException(Exception):
    pass


class TrelloUtils:

    def __init__(self, bot):
        self._key = Configuration.get_master_var("TRELLO_KEY")
        self._token = Configuration.get_master_var("TRELLO_TOKEN")
        self.bot = bot

    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3, logger='bugbot')
    async def _request(self, endpoint, payload={}, method='GET'):
        payload.update({'key': self._key, 'token': self._token})
        async with self.bot.aiosession.request(method, f'{API_BASE}{endpoint}', params=payload) as resp:
            if resp.status is not 200:
                resp_text = await resp.text()
                raise TrelloException(f'Unexpected response from Trello API ({resp.status}): {resp_text}')
            return await resp.json()

    # Gets basic data for a board
    async def get_board(self, board_id):
        ep = f'/boards/{board_id}'
        return await self._request(ep)

    # Gets basic data for a list
    async def get_list(self, list_id):
        ep = f'/lists/{list_id}'
        return await self._request(ep)

    # Gets data for a card (shortLink supported as ID)
    async def get_card(self, card_id):
        ep = f'/cards/{card_id}'
        return await self._request(ep)

    # Edit the title (short description) and/or content (everything else) on a card
    async def edit_card(self, id, title=None, content=None):
        ep = f'/cards/{id}'
        payload = {}
        if title is not None:
            payload['name'] = title
        if content is not None:
            payload['desc'] = content
        return await self._request(ep, payload, 'PUT')

    # Archive a card
    async def archive_card(self, card_id):
        ep = f'/cards/{card_id}'
        res = await self._request(ep, {'closed': True}, 'PUT')
        if res['closed']:
            return True
        return False

    # Unarchive a card
    async def unarchive_card(self, id):
        ep = f'/cards/{id}'
        res = await self._request(ep, {'closed': False}, 'PUT')
        if not res['closed']:
            return True
        return False

    # Add a card with a title (short description) and content (everything else). Will return the shortLink ID
    async def add_card(self, list_id, title, content):
        ep = '/cards'
        payload = {
            'idList': list_id,
            'name': title,
            'desc': content
        }
        res = await self._request(ep, payload, 'POST')
        return res['shortLink']

    # Move a card to another list or board. List ID is always required
    async def move_card(self, card_id, list_id, board_id=None):
        ep = f'/cards/{id}'
        payload = {
            'idList': list_id
        }
        if board_id is not None:
            payload['idBoard'] = board_id
        res = await self._request(ep, payload, 'PUT')
        return res['idList'] == list_id

    # Get all comments (e.g. notes/repros...etc) on a card
    async def get_comments(self, card_id):
        ep = f'/cards/{card_id}/actions'
        return await self._request(ep, {'filter': 'commentCard'})

    # Add a comment (e.g. note, repro...etc) to a card. Will return the comment ID for future edit/deletion purposes
    async def add_comment(self, card_id, comment):
        ep = f'/cards/{card_id}/actions/comments'
        res = await self._request(ep, {'text': comment}, 'POST')
        return res['id']

    # Edit a comment using the card ID and action/comment ID (returned when creating the comment)
    async def edit_comment(self, card_id, action_id):
        ep = f'/cards/{card_id}/actions/{action_id}/comments'
        res = await self._request(ep, {'text': comment}, 'PUT')
        return res['id']

    # Remove a comment using the card ID and action/comment ID (returned when creating the comment)
    async def remove_comment(self, card_id, action_id):
        ep = f'/cards/{card_id}/actions/{action_id}/comments'
        res = await self._request(ep, method='DELETE')
        return True

    # Add a link attachment to a card. Name should be the attacher's name and discrim
    async def add_attachment(self, card_id, name, url):
        ep = f'/cards/{card_id}/attachments'
        res = await self._request(ep, {'name': name, 'url': url}, 'POST')
        return res['id']

    # Remove an attachment from a card
    async def remove_attachment(self, card_id, attachment_id):
        ep = f'/cards/{card_id}/attachments/{attachment_id}'
        res = await self._request(ep, method='DELETE')
        return True

    # Add a label to a card
    async def add_label(self, card_id, label_id):
        ep = f'/cards/{card_id}/idLabels'
        return await self._request(ep, {'value': label_id}, 'POST')

    # Add a member to a card. Member ID is their Trello ID (not username)
    async def add_member(self, card_id, member_id):
        ep = f'/cards/{card_id}/idMembers'
        return await self._request(ep, {'value': member_id}, 'POST')

    # Remove a member from a card. Member ID is their Trello ID (not username)
    async def remove_member(self, card_id, member_id):
        ep = f'/cards/{card_id}/idMembers/{member_id}'
        return await self._request(ep, method='DELETE')
