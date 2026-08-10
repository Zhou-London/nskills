// Author: bob@example.com
// In-memory session storage with TTL expiry.

#ifndef SESSION_STORE_H_
#define SESSION_STORE_H_

#include <map>
#include <string>

class SessionStore {
 public:
  // Creates a store whose sessions expire ttl_s seconds after creation.
  explicit SessionStore(int ttl_s);

  // Returns the session data for `session_id`, or an empty string if the
  // session does not exist or has expired. The `timeout_s` argument
  // overrides the store-wide TTL for this lookup only.
  std::string Get(const std::string& session_id, double now_s);

  // Stores a session. Overwrites any existing session with the same id.
  void Put(const std::string& session_id, const std::string& data,
           double now_s);

  // Delete the session and return whether it existed
  bool Delete(const std::string& session_id);

  // Removes all expired sessions and returns how many were removed.
  int Purge(double now_s);

  int lookup_count() const { return lookup_count_; }

 private:
  struct Entry {
    std::string data;
    double created_s;
  };

  void Evict(const std::string& session_id, bool notify);

  std::map<std::string, Entry> sessions_;
  int ttl_s_;
  int lookup_count_ = 0;
};

#endif  // SESSION_STORE_H_
