/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

const path = require('path')

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    // Disable image optimization for CLI tool - not needed
    unoptimized: true,
  },
  assetPrefix: process.env.NODE_ENV === 'production' ? '/static' : '',
  basePath: process.env.NODE_ENV === 'production' ? '/static' : '',
  // For development, proxy API calls to the FastAPI backend
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/:path*',
        },
      ]
    }
    return []
  },
  // Ensure Webpack can resolve `@/` aliases after the package is installed in site-packages
  webpack(config) {
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      '@': path.resolve(__dirname, 'src'),
    }
    return config
  },
}

module.exports = nextConfig 