declare module 'kepler.gl' {
    import { ComponentType } from 'react';

    interface KeplerGlProps {
        id: string;
        mapboxApiAccessToken: string;
        width: number;
        height: number;
        appName: string;
        version: string;
        mapConfig?: any;
    }

    const KeplerGl: ComponentType<KeplerGlProps>;
    export default KeplerGl;
}

declare module 'kepler.gl/reducers' {
    const keplerGlReducer: any;
    export default keplerGlReducer;
} 