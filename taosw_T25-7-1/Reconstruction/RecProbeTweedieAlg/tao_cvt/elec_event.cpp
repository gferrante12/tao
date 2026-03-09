/*================================================================
*   Filename   : elec_event.cpp
*   Author     : Yuyi Wang
*   Created on  Tue 3 Jan 2023 17:32:30 PM CST
*   Description:
*
================================================================*/

#include "convert.hpp"

#include "Event/CdElecChannel.h"
#include "Event/CdElecEvt.h"
#include <iostream>
#include <stdexcept>

using namespace std;

struct CdElecChannel_t
{
    int64_t id;
    int32_t ChannelID;
    float ADC;
    float TDC;
    float Width;

    CdElecChannel_t(int64_t i, Tao::CdElecChannel* ch, size_t j)
    {
        id = i;
        ChannelID = ch->getChannelID();
        ADC = ch->getADCs()[j];
        TDC = ch->getTDCs()[j];
        Width = ch->getWidths()[j];
    }

    static const H5::DataType& get_h5_type()
    {
        static auto type = H5::CompType(sizeof(CdElecChannel_t));
#define INSERT(name) INSERT_(type, CdElecChannel_t, name)
        INSERT(id);
        INSERT(ChannelID);
        INSERT(ADC);
        INSERT(TDC);
        INSERT(Width);
#undef INSERT
        return type;
    }
};

SPEC_H5TYPE_IMPL(CdElecChannel_t)

void transform_elec_event(TTree* elec_tree, H5::Group& output, const H5::DSetCreatPropList& dsp)
{
    Tao::CdElecEvt* elec_event = nullptr;
    elec_tree->SetBranchAddress("CdElecEvt", &elec_event);
    auto count = elec_tree->GetEntries();
    auto group = output.createGroup("ElecEvent");
    auto channel_table = buffered_packet_table<CdElecChannel_t>(group, "Channel", count, dsp);
    cout << "Transforming ElecEvent..." << count << " in total." << endl;
    for (Long64_t i = 0; i < count; i++)
    {
        elec_tree->GetEntry(i);
        auto channels = elec_event->GetElecChannels();
        for (auto& ch : channels)
        {
            if (!(ch.getADCs().size() == ch.getTDCs().size() && ch.getADCs().size() == ch.getWidths().size()))
            {
                throw runtime_error("Invalid CdElecChannel");
            }
            for (size_t j = 0; j < ch.getADCs().size(); j++)
            {
                channel_table.push_back(CdElecChannel_t(i, &ch, j));
            }
        }
        if ((i + 1) % LOG_PROCESS_UNIT == 0)
        {
            cout << "Processed " << (i + 1) << " entries." << endl;
        }
    }
    cout << "Done." << endl;
}
