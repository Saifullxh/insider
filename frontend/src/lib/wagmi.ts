'use client';

import { http, createConfig, createStorage } from 'wagmi';
import { base } from 'wagmi/chains';

export const wagmiConfig = createConfig({
    chains: [base],
    storage: createStorage({ storage: typeof window !== 'undefined' ? localStorage : undefined }),
    transports: {
        [base.id]: http(),
    },
});
