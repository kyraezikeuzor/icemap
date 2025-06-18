import React, { useEffect, useState } from 'react';
import { Provider } from 'react-redux';
import { createStore, combineReducers } from 'redux';
import KeplerGl from 'kepler.gl';
import keplerGlReducer from 'kepler.gl/reducers';
import './App.css';

// Create store
const reducers = combineReducers({
  keplerGl: keplerGlReducer
});

const store = createStore(reducers);

function App() {
  const [mapboxApiAccessToken, setMapboxApiAccessToken] = useState<string>('');

  useEffect(() => {
    // You'll need to add your Mapbox token here
    // For now, we'll use a placeholder - you should replace this with your actual token
    setMapboxApiAccessToken('pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjbGV4YW1wbGUifQ.example');
  }, []);

  const mapConfig = {
    version: 'v1',
    config: {
      visState: {
        filters: [],
        layers: [],
        interactionConfig: {
          tooltip: {
            fieldsToShow: {},
            enabled: true
          },
          brush: {
            size: 0.5,
            enabled: false
          },
          geocoder: {
            enabled: false
          },
          coordinate: {
            enabled: false
          }
        },
        layerBlending: 'normal',
        splitMaps: [],
        animationConfig: {
          currentTime: null,
          speed: 1
        }
      },
      mapState: {
        bearing: 0,
        dragRotate: false,
        latitude: 39.8283, // Center on United States
        longitude: -98.5795, // Center on United States
        pitch: 0,
        zoom: 3.5, // Zoom level to show most of the US
        isSplit: false
      },
      mapStyle: {
        styleType: 'dark',
        topLayerGroups: {},
        visibleLayerGroups: {
          label: true,
          road: true,
          border: false,
          building: true,
          water: true,
          land: true,
          '3d building': false
        },
        threeDBuildingColor: [
          194,
          194,
          194
        ],
        mapStyles: {}
      }
    }
  };

  return (
    <Provider store={store}>
      <div className="App">
        <header className="App-header">
          <h1>IceMap Globe</h1>
          <p>A beautiful visualization of our world</p>
        </header>
        <main className="App-main">
          <KeplerGl
            id="map"
            mapboxApiAccessToken={mapboxApiAccessToken}
            width={window.innerWidth}
            height={window.innerHeight - 120}
            appName="IceMap"
            version="v1"
            mapConfig={mapConfig}
          />
        </main>
      </div>
    </Provider>
  );
}

export default App;
