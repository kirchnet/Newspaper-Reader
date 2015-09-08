#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>

#include "TtsEngine.h"

#define OUTPUT_BUFFER_SIZE (32 * 1024)

//ALSA-related additions 
#include "../alsa-lib-1.0.29/include/asoundlib.h"
static char *device = "default";			/* playback device */
snd_output_t *output = NULL;
int err;
snd_pcm_t *handle;
snd_pcm_sframes_t frames;
//end ALSA additions

using namespace android;

static bool synthesis_complete = false;

static FILE *outfp = stdout;
static FILE *infp, *langfp; 

// @param [inout] void *&       - The userdata pointer set in the original
//                                 synth call
// @param [in]    uint32_t      - Track sampling rate in Hz
// @param [in] tts_audio_format - The audio format
// @param [in]    int           - The number of channels
// @param [inout] int8_t *&     - A buffer of audio data only valid during the
//                                execution of the callback
// @param [inout] size_t  &     - The size of the buffer
// @param [in] tts_synth_status - indicate whether the synthesis is done, or
//                                 if more data is to be synthesized.
// @return TTS_CALLBACK_HALT to indicate the synthesis must stop,
//         TTS_CALLBACK_CONTINUE to indicate the synthesis must continue if
//            there is more data to produce.
tts_callback_status synth_done(void *& userdata, uint32_t sample_rate,
        tts_audio_format audio_format, int channels, int8_t *& data, size_t& size, tts_synth_status status)
{
	fprintf(stderr, "TTS callback, rate: %d, data size: %d, sizeof %d, status: %i\n", sample_rate, size, sizeof(data), status);

	if (status == TTS_SYNTH_DONE)
	{
		synthesis_complete = true;
	}

	if ((size == OUTPUT_BUFFER_SIZE) || (status == TTS_SYNTH_DONE))
	{
                frames = snd_pcm_writei(handle, data, size/2);
				fprintf(stderr, "Frames %d ",frames);
                if (frames < 0){
					fprintf(stderr, "Frames recover %d %s",frames,snd_strerror(err));
                    frames = snd_pcm_recover(handle, frames, 1);
				}
                if (frames < 0) {
                        fprintf(stderr, "snd_pcm_writei failed: %s\n", snd_strerror(err));
                        return TTS_CALLBACK_CONTINUE;
                }
                if (frames > 0 && frames < size/2)
                        fprintf(stderr, "Short write (expected %li, wrote %li)\n", (long)size, frames);
	}


	return TTS_CALLBACK_CONTINUE;
}

static void usage(void)
{
	fprintf(stderr, "\nUsage:\n\n" \
					"tts.alsa \n\n" \
		   			" refer to instructions on hackaday.io\n");
	exit(0);
}

int main(int argc, char *argv[])
{
	tts_result result;
	TtsEngine* ttsEngine = getTtsEngine();
	uint8_t* synthBuffer;
	char* synthInput = NULL;
	int currentOption;
	struct stat st;
        char* outputFilename = NULL;
	
	fprintf(stderr, "Pico TTS ALSA App\n");


	//Open teext file with text to be synthesized
	infp = fopen("temp.txt", "rt");
	if(infp==NULL) fprintf(stderr, "Can't open input file \n");
	fstat(fileno(infp),&st);
	fprintf(stderr, "File size %d\n", st.st_size);
	char buffer[st.st_size+1];
	int i=0;
	char ch;
	while((ch=fgetc(infp)) != EOF){
		buffer[i]=ch;
		if (i++>st.st_size) break;
	}
	buffer[st.st_size]='\0';
	fclose(infp);
	synthInput = buffer;
	//end open file

    if (!synthInput)
    {
    	fprintf(stderr, "Error: no input string\n");
    	usage();
    }

    fprintf(stderr, "Input string: \"%s\"\n", synthInput);

	synthBuffer = new uint8_t[OUTPUT_BUFFER_SIZE];

	result = ttsEngine->init(synth_done, "../lang/");

	if (result != TTS_SUCCESS)
	{
		fprintf(stderr, "Failed to init TTS\n");
	}

	// Load language from file
	langfp = fopen("language.txt", "rt");
	if(langfp==NULL) fprintf(stderr, "Can't open language configuration file \n");
	char langbuf[8];
	fread(langbuf,(size_t)sizeof(char),7,langfp);
	langbuf[7]='\0';
	langbuf[3]='\0';
	fclose(langfp);
	fprintf(stderr, "Language %s, country %s\n", langbuf, langbuf+4);
	result = ttsEngine->setLanguage(langbuf, langbuf+4, "");
//	result = ttsEngine->setLanguage("deu", "DEU", ""); //uncomment to hardcode language selection

	if (result != TTS_SUCCESS)
	{
		fprintf(stderr, "Failed to load language\n");
	}

	fprintf(stderr, "Synthesising text...\n");

	if ((err = snd_pcm_open(&handle, device, SND_PCM_STREAM_PLAYBACK, 0)) < 0) {
		fprintf(stderr, "Playback open error: %s\n", snd_strerror(err));
		exit(EXIT_FAILURE);
	}
	if ((err = snd_pcm_set_params(handle,
	                              SND_PCM_FORMAT_S16_LE,
	                              SND_PCM_ACCESS_RW_INTERLEAVED,
	                              1,
	                              16000,
	                              1,
	                              500000)) < 0) {	/* 0.5sec */
		fprintf(stderr, "Playback open error: %s\n", snd_strerror(err));
		exit(EXIT_FAILURE);
	}
		fprintf(stderr, "snd pcm msg: %s\n", snd_strerror(err));

	result = ttsEngine->synthesizeText(synthInput, synthBuffer, OUTPUT_BUFFER_SIZE, NULL);

	if (result != TTS_SUCCESS)
	{
		fprintf(stderr, "Failed to synth text\n");
	}

	while(!synthesis_complete)
	{
		usleep(100);
	}

	fprintf(stderr, "Completed.\n");


	result = ttsEngine->shutdown();

	if (result != TTS_SUCCESS)
	{
		fprintf(stderr, "Failed to shutdown TTS\n");
	}

	delete [] synthBuffer;
//ALSA cleanup
	snd_pcm_drain(handle);
	snd_pcm_close(handle);
//end ALSA cleanup
	return 0;
}
