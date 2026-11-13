import React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import CreateUserForm from "./CreateUserForm.jsx";
import UsersTable from "./UsersTable.jsx";
import { useUsers } from "./useUsers.js";

function Handover({ handover, onDone }) {
  return (
    <Alert variant="notice" role="status">
      <AlertTitle className="line-clamp-none">
        Give {handover.email} this one-time password: <code className="font-mono text-sm font-semibold">{handover.password}</code>
      </AlertTitle>
      <AlertDescription className="text-inherit">
        It's shown only now. They'll be asked to change it when they sign in.
        <Button variant="link" className="h-auto p-0 text-inherit" onClick={onDone}>Done</Button>
      </AlertDescription>
    </Alert>
  );
}

// Admin only: create read-only or read-and-write users, change their access, reset or remove them.
export default function UsersPage({ me }) {
  const u = useUsers();
  return (
    <>
      <CreateUserForm onCreate={u.create} />
      {u.handover && <Handover handover={u.handover} onDone={u.dismissHandover} />}
      {u.error && <p className="form-error" role="alert">{u.error}</p>}
      <Card>
        <CardHeader><CardTitle>Users</CardTitle></CardHeader>
        {!u.users ? <Skeleton className="h-5 w-60" /> : (
          <UsersTable users={u.users} me={me} onRoleChange={u.changeRole} onReset={u.resetPassword} onRemove={u.remove} />
        )}
      </Card>
    </>
  );
}
