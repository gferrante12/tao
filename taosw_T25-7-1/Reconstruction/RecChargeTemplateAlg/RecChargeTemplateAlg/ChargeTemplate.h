#ifndef ChargeTemplate_h
#define ChargeTemplate_h

#include "TH1F.h"
#include "TFile.h"
#define TEMPLATENUM 101
#include <string>
#include <vector>

/*
 * ChargeTemplate
 */

class ChargeTemplate
{
    public:
        ChargeTemplate(std::string charge_template_file);
        ~ChargeTemplate();

        bool initialize();
        bool finalize();

        float LinearInterpolation(float radius, float x0, float y0, float x1, float y1);
        int FindBeforeIndex(float radius, int low, int high);
        float get_template_radius(int index);
        TH1F* get_template(int index);
        float CalExpChargeHit(float radius, float theta);
        float cal_sipm_proj(float radius, float theta);
        float cal_sipm_distance(float radius, float theta);

    private:
        int tmp_num;
        float cd_radius;
        float sipm_radius;
        float max_tmp_radius;
        int tmp_numbers;
        std::vector<float> tmp_radius;
        std::vector<TH1F*> tmp;
        TFile* tmp_file;
        std::string charge_template_file;
};

#endif
