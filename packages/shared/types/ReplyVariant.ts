/**
 * ReplyVariant
 * One generated reply option for the freelancer to send to a client.
 * Mirror of backend app/schemas/reply.py :: ReplyVariant
 */
export type ReplyType = "short" | "warm" | "expert";

export interface ReplyVariant {
  type: ReplyType;
  text: string;
  includes_link: boolean;
  landing_slug: string | null;
}
