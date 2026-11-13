import { useCallback, useEffect, useState } from "react";
import { createUser, fetchUsers, removeUser, updateUser } from "@/api/admin.js";
import { newPassword } from "./password.js";

// The user list and every change to it. `handover` is a one-time password to show the admin once.
export function useUsers() {
  const [users, setUsers] = useState(null);
  const [error, setError] = useState(null);
  const [handover, setHandover] = useState(null);

  const load = useCallback(() => fetchUsers().then(setUsers).catch((e) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);
  const act = (promise) => promise.then(load).catch((e) => setError(e.message));

  return {
    users, error, handover,
    dismissHandover: () => setHandover(null),
    // create rejects on failure, so the form can show the error next to itself
    create: (form) => createUser(form).then((u) => { setHandover({ email: u.email, password: form.password }); load(); }),
    changeRole: (u, role) => act(updateUser(u.email, { role })),
    resetPassword: (u) => {
      const password = newPassword();
      act(updateUser(u.email, { password }).then(() => setHandover({ email: u.email, password })));
    },
    remove: (u) => act(removeUser(u.email)),
  };
}
