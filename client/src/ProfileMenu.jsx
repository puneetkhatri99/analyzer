import React from "react";
import { ChevronDown } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// The signed-in user's menu: who they are, their access, and the account actions.
export default function ProfileMenu({ email, roleText, onChangePassword, onSignOut }) {
  const initial = email[0].toUpperCase();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="profile-button" aria-label={`Profile: ${email}`}>
        <Avatar className="size-[30px]"><AvatarFallback className="bg-primary text-sm font-semibold text-primary-foreground">{initial}</AvatarFallback></Avatar>
        <ChevronDown className="size-3" aria-hidden="true" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[min(300px,calc(100vw-32px))] p-1.5">
        <DropdownMenuLabel className="flex items-center gap-3 px-2.5 pt-2.5 pb-3 font-normal">
          <Avatar className="size-10"><AvatarFallback className="bg-primary text-[17px] font-semibold text-primary-foreground">{initial}</AvatarFallback></Avatar>
          <span className="grid min-w-0">
            <strong className="truncate font-semibold">{email}</strong>
            <span className="profile-role">{roleText}</span>
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem className="px-2.5 py-2" onSelect={onChangePassword}>Change password</DropdownMenuItem>
        <DropdownMenuItem className="px-2.5 py-2" onSelect={onSignOut}>Sign out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
