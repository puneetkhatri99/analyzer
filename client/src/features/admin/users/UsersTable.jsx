import React from "react";
import Confirm from "@/components/Confirm.jsx";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { longDate } from "@/lib/format.js";
import { ROLE_TEXT } from "../access.js";
import AccessSelect from "./AccessSelect.jsx";

function UserActions({ user, onReset, onRemove }) {
  return (
    <span className="inline-flex gap-1">
      <Confirm title={`Reset the password for ${user.email}?`} action="Reset password" danger={false} onConfirm={onReset}
        description="Their current password stops working and they're signed out. You'll get a new one-time password to give them.">
        <Button variant="ghost" size="sm">Reset password</Button>
      </Confirm>
      <Confirm title={`Remove ${user.email}?`} action="Remove" onConfirm={onRemove} description="They will be signed out and can't sign in again.">
        <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">Remove</Button>
      </Confirm>
    </span>
  );
}

// Admin accounts can't be changed here; they come only from the server's create_admin command.
export default function UsersTable({ users, me, onRoleChange, onReset, onRemove }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Email</TableHead><TableHead>Access</TableHead><TableHead>Status</TableHead><TableHead>Added</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {users.map((u) => {
          const admin = u.role === "admin";
          return (
            <TableRow key={u.email}>
              <TableCell>{u.email}{u.email === me && <span className="muted"> (you)</span>}</TableCell>
              <TableCell className="min-w-40">
                {admin ? <Badge>{ROLE_TEXT.admin}</Badge> : <AccessSelect value={u.role} label={`Access for ${u.email}`} onChange={(role) => onRoleChange(u, role)} />}
              </TableCell>
              <TableCell>
                {u.must_change_password ? <Badge variant="outline">Waiting for first sign-in</Badge> : <Badge variant="secondary">Active</Badge>}
              </TableCell>
              <TableCell className="muted">{longDate(u.created_at)}{u.created_by ? ` by ${u.created_by}` : ""}</TableCell>
              <TableCell className="text-right">
                {!admin && <UserActions user={u} onReset={() => onReset(u)} onRemove={() => onRemove(u)} />}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
