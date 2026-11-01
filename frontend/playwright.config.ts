import {defineConfig} from '@playwright/test'
export default defineConfig({testDir:'./e2e',globalSetup:'./e2e/setup.ts',timeout:45000,use:{baseURL:'http://127.0.0.1:5173',headless:true,launchOptions:{executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'}},reporter:'list'})
