import type { MediaReference } from '../../document';
import type { VideoEmbedContent } from '../../types';
type $$ComponentProps = {
    content: VideoEmbedContent;
    media?: Record<string, MediaReference>;
};
declare const VideoEmbed: import("svelte").Component<$$ComponentProps, {}, "">;
type VideoEmbed = ReturnType<typeof VideoEmbed>;
export default VideoEmbed;
