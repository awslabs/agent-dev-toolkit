/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

declare module 'dompurify' {
  interface DOMPurifyI {
    sanitize(dirty: string, options?: Record<string, any>): string;
  }

  const DOMPurify: DOMPurifyI;
  export default DOMPurify;
} 