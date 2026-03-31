import type { Snippet } from 'svelte';
import type { HTMLAttributes } from 'svelte/elements';
interface Props extends HTMLAttributes<HTMLDivElement> {
    children?: Snippet;
    class?: string;
}
declare const Card: import("svelte").Component<Props, {}, "">;
type Card = ReturnType<typeof Card>;
export default Card;
