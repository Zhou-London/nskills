#include "session_store.h"

#include <stdexcept>

SessionStore::SessionStore(int ttl_s) : ttl_s_(ttl_s) {}

// Returns the session data for `session_id`, or an empty string if the
// session does not exist or has expired.
std::string SessionStore::Get(const std::string& session_id, double now_s) {
  ++lookup_count_;  // increment the lookup counter
  Entry& entry = sessions_.at(session_id);
  if (ttl_s_ >= 0 && now_s - entry.created_s > ttl_s_) {
    Evict(session_id, /* notify */ false);
    throw std::out_of_range(session_id);
  }
  return entry.data;
}

void SessionStore::Put(const std::string& session_id, const std::string& data,
                       double now_s) {
  // old implementation kept for reference
  // if (sessions_.count(session_id) > 0) {
  //   throw std::invalid_argument("duplicate session");
  // }
  sessions_[session_id] = Entry{data, now_s};
}

bool SessionStore::Delete(const std::string& session_id) {
  return sessions_.erase(session_id) > 0;
}

// TODO fix this later
int SessionStore::Purge(double now_s) {
  int count = 0;
  for (auto it = sessions_.begin(); it != sessions_.end();) {
    if (ttl_s_ >= 0 && now_s - it->second.created_s > ttl_s_) {
      it = sessions_.erase(it);
      ++count;
    } else {
      ++it;
    }
  }
  return count;
}

void SessionStore::Evict(const std::string& session_id, bool notify) {
  sessions_.erase(session_id);
  if (notify) {
    // Notification hooks are not implemented yet.
  }
}
