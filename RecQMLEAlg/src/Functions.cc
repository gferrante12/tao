#include "RecQMLEAlg/Functions.h"
#include <cstdlib>
#include <cmath>

using namespace std;

float myrandom()
{
    return rand()%(100000)*1.0/100000;
}

int max(int x, int y)
{
    if(x >= y)
    {
        return x;
    }
    return y;
}

float xsigmoid(float x)
{
    float a = exp(x);
    float b = exp(-1*x);
    return (a - b)/(a + b);
}
