/*================================================================
 *   Filename   : main.cpp
 *   Author     : Yiyang Wu, Yuyi Wang
 *   Created on  Wed 28 Oct 2020 03:38:40 PM CST
 *   Description:
 *
 ================================================================*/
#include "convert.hpp"

#include "TDirectoryFile.h"
#include "TFile.h"
#include "TTree.h"

#include "H5Cpp.h"
#include <boost/program_options.hpp>
#include <boost/program_options/options_description.hpp>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#define ZSTD_FILTER 32015

using namespace std;
namespace po = boost::program_options;

// A program to convert raw data from a root file of JP1t to hdf5

int main(int argc, char** argv)
{
    // Parsing Arguments
    po::options_description program("juno_cvt");
    program.add_options()(
        "help,h", "Help")(
        "input,i", po::value<string>(), "Input ROOT file")(
        "output,o", po::value<string>(), "Output H5 file")(
        "type,t", po::value<string>(), "Input file type, valid option: detsim, elecsim, calib, rec")(
        "compress,c", po::value<unsigned int>()->default_value(4), "compression level");

    po::variables_map vm;
    po::store(po::parse_command_line(argc, argv, program), vm);
    po::notify(vm);
    if (vm.count("help"))
    {
        cout << program << endl;
        return 1;
    }
    auto inputfilename = vm["input"].as<string>();
    auto outputfilename = vm["output"].as<string>();
    auto type = vm["type"].as<string>();
    unsigned int compression_level = vm["compress"].as<unsigned int>();

    // Create output file
    auto output = H5::H5File(outputfilename, H5F_ACC_TRUNC);
    // Set H5 compression level
    auto dsp = H5::DSetCreatPropList();
    if (H5Zfilter_avail(ZSTD_FILTER))
    {
        dsp.setFilter(ZSTD_FILTER, 0b00, 1, &compression_level);
    }
    else
    {
        cerr << "No zstd support! Please check if HDF5_PLUGIN_PATH is valid." << endl;
        if (H5Zfilter_avail(H5Z_FILTER_DEFLATE))
        {
            dsp.setDeflate(compression_level);
        }
        else
        {
            cerr << "No gzip support! The data will not compressed." << endl;
        }
    }

    TFile* input = new TFile(inputfilename.c_str(), "read");

    if (type == "detsim")
    {
        auto sim_header = input->Get<TTree>("Event/Sim/SimHeader");
        auto sim_event = input->Get<TTree>("Event/Sim/SimEvt");

        if (sim_header) transform_sim_header(sim_header, output, dsp);
        if (sim_event) transform_sim_event(sim_event, output, dsp);
    }
    else if (type == "elecsim")
    {
        auto elec_event = input->Get<TTree>("Event/Elec/CdElecEvt");

        if (elec_event) transform_elec_event(elec_event, output, dsp);
    }
    else
    {
        cerr << "Invalid type: " << type << endl;
    }

    input->Close();
    cout << "Done: " << inputfilename << " -> " << outputfilename << endl;
    return 0;
}
