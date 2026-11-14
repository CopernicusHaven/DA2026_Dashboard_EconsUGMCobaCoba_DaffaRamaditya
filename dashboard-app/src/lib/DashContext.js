import { createContext, useContext } from 'react';

export const Dash = createContext(null);
export const useDash = () => useContext(Dash);
