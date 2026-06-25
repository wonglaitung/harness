package com.harness.core;

/**
 * Statistics for streaming session.
 */
public class StreamingStats {

    private int chunksReceived = 0;
    private int chunksProcessed = 0;
    private int backpressureEvents = 0;
    private double totalPauseTime = 0.0;
    private int bufferHighWatermark = 0;

    public int getChunksReceived() {
        return chunksReceived;
    }

    public int getChunksProcessed() {
        return chunksProcessed;
    }

    public int getBackpressureEvents() {
        return backpressureEvents;
    }

    public double getTotalPauseTime() {
        return totalPauseTime;
    }

    public int getBufferHighWatermark() {
        return bufferHighWatermark;
    }

    public void incrementChunksReceived() {
        chunksReceived++;
    }

    public void incrementChunksProcessed() {
        chunksProcessed++;
    }

    public void incrementBackpressureEvents() {
        backpressureEvents++;
    }

    public void addPauseTime(double time) {
        totalPauseTime += time;
    }

    public void updateHighWatermark(int bufferSize) {
        if (bufferSize > bufferHighWatermark) {
            bufferHighWatermark = bufferSize;
        }
    }

    /**
     * Check if streaming is healthy (no excessive backpressure).
     */
    public boolean isHealthy() {
        return backpressureEvents < 10;
    }

    public void reset() {
        chunksReceived = 0;
        chunksProcessed = 0;
        backpressureEvents = 0;
        totalPauseTime = 0.0;
        bufferHighWatermark = 0;
    }
}
