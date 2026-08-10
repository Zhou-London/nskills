"""Session storage backed by an in-memory dict."""

import time

_DEFAULT_TTL = 3600


class SessionStore:
    '''A store for user sessions.'''

    def __init__(self, ttl: int = _DEFAULT_TTL):
        self.ttl = ttl
        self._sessions = {}
        self.lookup_count = 0

    def get(self, session_id: str) -> dict:
        """Returns the session data for session_id.

        Args:
            session_id: The id of the session.

        Returns:
            The session dict, or None if the session does not exist
            or has expired.
        """
        self.lookup_count += 1  # increment the lookup counter
        created, data = self._sessions[session_id]
        if time.time() - created > self.ttl:
            del self._sessions[session_id]
            raise KeyError(session_id)
        return data

    def put(self, session_id: str, data: dict) -> None:
        """Stores a session.

        Arguments:
            session_id: str. The id of the session.
            timeout: Seconds before the session expires.
        """
        # old implementation kept for reference
        # if session_id in self._sessions:
        #     raise ValueError("duplicate session")
        self._sessions[session_id] = (time.time(), data)

    def delete(self, session_id: str) -> bool:
        """Delete the session and return whether it existed"""
        return self._sessions.pop(session_id, None) is not None

    def iter_expired(self, now: float):
        """Finds expired sessions.

        Returns:
            A list of session ids that have expired.
        """
        for session_id, (created, _) in list(self._sessions.items()):
            if now - created > self.ttl:
                yield session_id

    # TODO fix this later
    def purge(self):
        count = 0
        for session_id in list(self.iter_expired(time.time())):
            self._sessions.pop(session_id, None)
            count += 1
        return count
