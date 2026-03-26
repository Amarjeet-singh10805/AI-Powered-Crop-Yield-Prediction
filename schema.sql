 
CREATE DATABASE IF NOT EXISTS crop_yield
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE crop_yield;

CREATE TABLE IF NOT EXISTS prediction_history (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    crop            VARCHAR(100)  NOT NULL,
    season          VARCHAR(50)   NOT NULL,
    state           VARCHAR(100)  NOT NULL,
    area            FLOAT         NOT NULL COMMENT 'Hectares',
    rainfall        FLOAT         NOT NULL COMMENT 'mm/year',
    fertilizer      FLOAT         NOT NULL COMMENT 'kg/ha',
    pesticide       FLOAT         NOT NULL COMMENT 'kg/ha',
    predicted_yield FLOAT         NOT NULL COMMENT 'tons/ha',
    INDEX idx_crop   (crop),
    INDEX idx_state  (state),
    INDEX idx_season (season),
    INDEX idx_date   (created_at)
);
