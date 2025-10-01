<?php
/**
 * Enqueue Divi Child theme scripts and styles
 */

function dwc_enqueue_chatbot() {
    // Load chatbot JavaScript (minified version)
    wp_enqueue_script(
        'dwc-chatbot',
        get_stylesheet_directory_uri() . '/chatbot.min.js',
        array(), // No dependencies
        filemtime(get_stylesheet_directory() . '/chatbot.min.js'),
        true // Load in footer
    );

    // Load chatbot CSS (minified if available)
    if (file_exists(get_stylesheet_directory() . '/style.min.css')) {
        wp_enqueue_style(
            'dwc-chatbot-style',
            get_stylesheet_directory_uri() . '/style.min.css',
            array(),
            filemtime(get_stylesheet_directory() . '/style.min.css')
        );
    } else {
        wp_enqueue_style(
            'dwc-chatbot-style',
            get_stylesheet_directory_uri() . '/style.css',
            array(),
            filemtime(get_stylesheet_directory() . '/style.css')
        );
    }
}
add_action('wp_enqueue_scripts', 'dwc_enqueue_chatbot');
