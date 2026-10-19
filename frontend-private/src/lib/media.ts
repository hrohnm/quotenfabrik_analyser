// API-Football media (no quota, but rate limited). Rendered through next/image, which caches them.
const MEDIA = "https://media.api-sports.io/football";

export const teamLogo = (id: number) => `${MEDIA}/teams/${id}.png`;
export const leagueLogo = (id: number) => `${MEDIA}/leagues/${id}.png`;
export const playerPhoto = (id: number) => `${MEDIA}/players/${id}.png`;
