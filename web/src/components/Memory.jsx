import React, { useEffect, useState } from "react";
import { getJSON } from "../api.js";

// Per-user memory, refreshed after each chat (via `bump`). Switch the User in the
// header and watch memory change: proof that state is isolated per user.
export default function Memory({ userId, bump }) {
  const [memory, setMemory] = useState("");
  useEffect(() => {
    getJSON(`/api/memory?user_id=${encodeURIComponent(userId)}`)
      .then((d) => setMemory(d.memory))
      .catch(() => setMemory(""));
  }, [userId, bump]);

  return (
    <div className="panel">
      <p className="panel-hint">Long-term memory for <b>{userId}</b>: a plain file the agent appends to.</p>
      {memory.trim() ? <pre className="memory">{memory}</pre> : <div className="empty">No memories yet. Ask the agent to remember something.</div>}
    </div>
  );
}
