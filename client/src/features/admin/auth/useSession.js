import { useCallback, useEffect, useState } from "react";
import { fetchMe, signOut as apiSignOut } from "@/api/admin.js";

// The signed-in admin user: undefined while checking, null when signed out.
export function useSession() {
  const [user, setUser] = useState(undefined);
  const refresh = useCallback(() => fetchMe().then(setUser).catch(() => setUser(null)), []);
  useEffect(() => { refresh(); }, [refresh]);
  const signOut = () => apiSignOut().finally(() => setUser(null));
  return { user, setUser, refresh, signOut };
}
