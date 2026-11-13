import * as React from "react"
import { cn } from "@/lib/utils"

// `as` lets a card be a <section> or <form>
function Card({
  className,
  as: Comp = "div",
  ...props
}) {
  return (
    <Comp
      data-slot="card"
      className={cn(
        "flex min-w-0 flex-col rounded-lg border bg-card p-5 text-card-foreground",
        className
      )}
      {...props}
    />
  )
}

function CardHeader({
  className,
  ...props
}) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "mb-3.5 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1",
        className
      )}
      {...props}
    />
  )
}

function CardTitle({
  className,
  ...props
}) {
  return (
    <h2
      data-slot="card-title"
      className={cn("m-0 text-base leading-6 font-semibold", className)}
      {...props}
    />
  )
}

function CardDescription({
  className,
  ...props
}) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-xs whitespace-nowrap text-muted-foreground", className)}
      {...props}
    />
  )
}

function CardAction({
  className,
  ...props
}) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        "col-start-2 row-span-2 row-start-1 self-start justify-self-end",
        className
      )}
      {...props}
    />
  )
}

function CardContent({
  className,
  ...props
}) {
  return (
    <div
      data-slot="card-content"
      className={cn("min-w-0", className)}
      {...props}
    />
  )
}

function CardFooter({
  className,
  ...props
}) {
  return (
    <div
      data-slot="card-footer"
      className={cn("mt-auto flex items-center pt-3", className)}
      {...props}
    />
  )
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
}
