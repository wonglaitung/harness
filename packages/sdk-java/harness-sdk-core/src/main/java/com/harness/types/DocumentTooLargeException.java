package com.harness.types;

/**
 * Exception thrown when document size exceeds the configured limit.
 */
public class DocumentTooLargeException extends RuntimeException {

    private final String filename;
    private final long size;
    private final long limit;

    /**
     * Create a new DocumentTooLargeException.
     *
     * @param filename Name of the document that exceeded the limit
     * @param size Actual size of the document in bytes
     * @param limit Configured size limit in bytes
     */
    public DocumentTooLargeException(String filename, long size, long limit) {
        super(String.format("Document '%s' (%.1fMB) exceeds limit (%.1fMB)",
            filename, size / 1024.0 / 1024, limit / 1024.0 / 1024));
        this.filename = filename;
        this.size = size;
        this.limit = limit;
    }

    /**
     * Get the filename of the oversized document.
     */
    public String getFilename() {
        return filename;
    }

    /**
     * Get the actual size of the document in bytes.
     */
    public long getSize() {
        return size;
    }

    /**
     * Get the configured size limit in bytes.
     */
    public long getLimit() {
        return limit;
    }
}
